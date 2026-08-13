"""消费分析服务：账单导入、AI打标、弹性预算、复盘报告、预算提醒"""
import csv
import io
import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consume import ConsumeRecord, Budget, BudgetTransfer, MonthlyReview, BudgetAlert
from app.utils.llm import get_llm


class ConsumeAnalyzer:
    """消费分析引擎"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 账单导入 ====================

    async def parse_wechat_bill(self, content: str) -> list[dict[str, Any]]:
        """解析微信账单CSV（兼容多种格式）"""
        records = []
        try:
            # 清理BOM和空白
            content = content.strip().lstrip('﻿')
            reader = csv.DictReader(io.StringIO(content))
            if not reader.fieldnames:
                return records

            # 自动识别列名（兼容中英文）
            field_map = {}
            for fname in reader.fieldnames:
                fname_clean = fname.strip().lower()
                if '时间' in fname_clean or 'time' in fname_clean:
                    field_map['time'] = fname
                elif '对方' in fname_clean or 'merchant' in fname_clean or '交易对方' in fname_clean:
                    field_map['merchant'] = fname
                elif '商品' in fname_clean or '描述' in fname_clean or 'description' in fname_clean:
                    field_map['description'] = fname
                elif '金额' in fname_clean or 'amount' in fname_clean:
                    field_map['amount'] = fname
                elif '收/支' in fname_clean or 'type' in fname_clean or '收支' in fname_clean:
                    field_map['io_type'] = fname
                elif '分类' in fname_clean or 'category' in fname_clean:
                    field_map['category'] = fname

            for row in reader:
                # 获取金额
                amount_key = field_map.get('amount', '')
                amount_str = row.get(amount_key, '').strip() if amount_key else ''
                if not amount_str:
                    continue
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue

                # 只导入支出
                io_key = field_map.get('io_type', '')
                if io_key:
                    io_type = row.get(io_key, '').strip()
                    if io_type == '收入':
                        continue

                # 时间
                time_key = field_map.get('time', '')
                time_str = row.get(time_key, '').strip() if time_key else ''
                try:
                    occurred_at = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        occurred_at = datetime.strptime(time_str, '%Y-%m-%d')
                    except ValueError:
                        occurred_at = datetime.utcnow()

                merchant = row.get(field_map.get('merchant', ''), '').strip() or None
                description = row.get(field_map.get('description', ''), '').strip() or None

                records.append({
                    'amount': amount,
                    'merchant': merchant,
                    'description': description,
                    'occurred_at': occurred_at.isoformat(),
                    'source': 'wechat',
                    'raw_data': {k: v for k, v in row.items()},
                })
        except Exception as e:
            raise ValueError(f"微信账单解析失败: {e}")

        return records

    async def parse_alipay_bill(self, content: str) -> list[dict[str, Any]]:
        """解析支付宝账单CSV"""
        records = []
        try:
            # 支付宝账单可能有BOM头
            if content.startswith('﻿'):
                content = content[1:]

            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                # 支付宝格式：交易时间, 交易分类, 交易对方, 商品名称, 收入, 支出, 账户, 备注
                amount_str = row.get('支出', '').strip()
                if not amount_str:
                    amount_str = row.get('金额', '').strip()
                if not amount_str:
                    continue
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue

                time_str = row.get('交易时间', '').strip() or row.get('时间', '').strip()
                try:
                    occurred_at = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        occurred_at = datetime.strptime(time_str, '%Y-%m-%d')
                    except ValueError:
                        occurred_at = datetime.utcnow()

                category = row.get('交易分类', '').strip() or None
                merchant = row.get('交易对方', '').strip() or None
                description = row.get('商品名称', '').strip() or None

                records.append({
                    'amount': amount,
                    'category': self._map_alipay_category(category),
                    'merchant': merchant,
                    'description': description,
                    'occurred_at': occurred_at.isoformat(),
                    'source': 'alipay',
                    'raw_data': row,
                })
        except Exception as e:
            raise ValueError(f"支付宝账单解析失败: {e}")

        return records

    @staticmethod
    def _map_alipay_category(category: str | None) -> str:
        """映射支付宝分类到系统分类"""
        if not category:
            return 'other'
        mapping = {
            '餐饮美食': 'food', '美食': 'food', '餐饮': 'food',
            '购物消费': 'shopping', '购物': 'shopping', '服饰鞋包': 'shopping',
            '交通出行': 'transport', '交通': 'transport', '打车': 'transport', '地铁': 'transport',
            '休闲娱乐': 'entertainment', '娱乐': 'entertainment', '电影': 'entertainment',
            '学习培训': 'study', '教育': 'study', '书籍': 'study',
            '住房物业': 'rent', '房租': 'rent', '物业': 'rent',
            '医疗健康': 'medical', '医疗': 'medical', '药品': 'medical',
            '生活缴费': 'utilities', '水电': 'utilities',
        }
        return mapping.get(category, 'other')

    async def import_records(self, records: list[dict]) -> int:
        """批量导入消费记录"""
        count = 0
        for rec in records:
            record = ConsumeRecord(
                user_id=self.user_id,
                amount=rec['amount'],
                category=rec.get('category', 'other'),
                merchant=rec.get('merchant'),
                description=rec.get('description'),
                source=rec.get('source', 'manual'),
                raw_data=rec.get('raw_data'),
                occurred_at=datetime.fromisoformat(rec['occurred_at']) if 'occurred_at' in rec else datetime.utcnow(),
            )
            self.session.add(record)
            count += 1
        await self.session.flush()
        return count

    # ==================== AI自动打标 ====================

    async def auto_tag_record(self, record: ConsumeRecord) -> str:
        """AI自动给消费打标签"""
        # 基于规则的简单打标（无需LLM）
        amount = record.amount
        category = record.category
        merchant = record.merchant or ''

        # 固定开支
        if category in ('rent', 'utilities', 'insurance'):
            return 'fixed'

        # 医疗、维修等刚需
        if category in ('medical', 'repair', 'education'):
            return 'necessity'

        # 高金额娱乐/购物 → 冲动
        if category in ('entertainment', 'shopping') and amount > 200:
            return 'impulse'

        # 大量购买同一商品 → 囤货
        if '箱' in merchant or '批' in merchant or amount > 500:
            return 'hoarding'

        # 餐饮、交通 → 刚需
        if category in ('food', 'transport'):
            return 'necessity'

        # 默认
        return 'necessity'

    async def batch_tag_records(self, month: str | None = None) -> int:
        """批量打标"""
        if not month:
            month = datetime.utcnow().strftime('%Y-%m')

        result = await self.session.execute(
            select(ConsumeRecord).where(
                and_(
                    ConsumeRecord.user_id == self.user_id,
                    ConsumeRecord.tag == None,
                    func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                )
            )
        )
        count = 0
        for record in result.scalars().all():
            tag = await self.auto_tag_record(record)
            record.tag = tag
            record.is_impulse = (tag == 'impulse')
            record.is_waste = (tag in ('impulse', 'hoarding'))
            count += 1

        await self.session.flush()
        return count

    # ==================== 弹性预算 ====================

    async def handle_flexible_budget(self, record: ConsumeRecord) -> dict[str, Any] | None:
        """处理弹性预算：突发刚需自动从娱乐额度划拨"""
        if record.category not in ('medical', 'repair', 'emergency'):
            return None

        month = record.occurred_at.strftime('%Y-%m')

        # 查找弹性预算
        result = await self.session.execute(
            select(Budget).where(
                and_(
                    Budget.user_id == self.user_id,
                    Budget.effective_month == month,
                    Budget.is_flexible == True,
                    Budget.category == record.category,
                )
            )
        )
        budget = result.scalar_one_or_none()
        if not budget:
            return None

        # 查找来源品类余额
        source_cats = budget.flex_source_categories or ['entertainment', 'shopping']
        for source_cat in source_cats:
            source_budget = await self.session.execute(
                select(Budget).where(
                    and_(
                        Budget.user_id == self.user_id,
                        Budget.effective_month == month,
                        Budget.category == source_cat,
                    )
                )
            )
            sb = source_budget.scalar_one_or_none()
            if not sb:
                continue

            # 计算来源品类已用
            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(ConsumeRecord.amount), 0)).where(
                    and_(
                        ConsumeRecord.user_id == self.user_id,
                        ConsumeRecord.category == source_cat,
                        func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                    )
                )
            )
            source_spent = spent_result.scalar() or 0
            source_remaining = sb.monthly_limit - source_spent

            if source_remaining >= record.amount:
                # 划拨
                transfer = BudgetTransfer(
                    user_id=self.user_id,
                    from_category=source_cat,
                    to_category=record.category,
                    amount=record.amount,
                    reason=f"突发{record.category}支出: {record.merchant or record.description or ''}",
                    effective_month=month,
                )
                self.session.add(transfer)
                await self.session.flush()
                return {
                    "transferred": True,
                    "from": source_cat,
                    "to": record.category,
                    "amount": record.amount,
                }

        return {"transferred": False, "reason": "无可用弹性额度"}

    # ==================== 月度复盘 ====================

    async def generate_monthly_review(self, month: str | None = None) -> MonthlyReview:
        """生成月度消费复盘报告"""
        if not month:
            month = datetime.utcnow().strftime('%Y-%m')

        # 总消费
        total_result = await self.session.execute(
            select(func.coalesce(func.sum(ConsumeRecord.amount), 0)).where(
                and_(
                    ConsumeRecord.user_id == self.user_id,
                    func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                )
            )
        )
        total_spent = total_result.scalar() or 0

        # 总预算
        budget_result = await self.session.execute(
            select(func.coalesce(func.sum(Budget.monthly_limit), 0)).where(
                and_(Budget.user_id == self.user_id, Budget.effective_month == month)
            )
        )
        total_budget = budget_result.scalar() or 0

        # 分类统计
        cat_result = await self.session.execute(
            select(ConsumeRecord.category, func.sum(ConsumeRecord.amount), func.count(ConsumeRecord.id)).where(
                and_(
                    ConsumeRecord.user_id == self.user_id,
                    func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                )
            ).group_by(ConsumeRecord.category)
        )
        category_breakdown = {}
        for row in cat_result.all():
            category_breakdown[row[0]] = {"total": float(row[1]), "count": row[2]}

        # 标签统计
        tag_result = await self.session.execute(
            select(ConsumeRecord.tag, func.sum(ConsumeRecord.amount), func.count(ConsumeRecord.id)).where(
                and_(
                    ConsumeRecord.user_id == self.user_id,
                    func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                    ConsumeRecord.tag != None,
                )
            ).group_by(ConsumeRecord.tag)
        )
        tag_breakdown = {}
        for row in tag_result.all():
            tag_breakdown[row[0]] = {"total": float(row[1]), "count": row[2]}

        # 无效消费
        waste_result = await self.session.execute(
            select(ConsumeRecord).where(
                and_(
                    ConsumeRecord.user_id == self.user_id,
                    ConsumeRecord.is_waste == True,
                    func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                )
            ).order_by(ConsumeRecord.amount.desc())
        )
        waste_items = [
            {"title": r.merchant or r.description or r.category, "amount": r.amount, "tag": r.tag}
            for r in waste_result.scalars().all()
        ]

        # 生成建议
        suggestions = self._generate_suggestions(category_breakdown, tag_breakdown, total_spent, total_budget)

        # 汇总
        surplus = total_budget - total_spent
        summary = f"本月消费¥{total_spent:.0f}，预算¥{total_budget:.0f}，{'结余' if surplus >= 0 else '超支'}¥{abs(surplus):.0f}。"

        # 保存或更新
        existing = await self.session.execute(
            select(MonthlyReview).where(
                and_(MonthlyReview.user_id == self.user_id, MonthlyReview.month == month)
            )
        )
        review = existing.scalar_one_or_none()
        if review:
            review.total_spent = total_spent
            review.total_budget = total_budget
            review.surplus = surplus
            review.category_breakdown = category_breakdown
            review.tag_breakdown = tag_breakdown
            review.waste_items = waste_items
            review.suggestions = suggestions
            review.summary = summary
        else:
            review = MonthlyReview(
                user_id=self.user_id, month=month,
                total_spent=total_spent, total_budget=total_budget, surplus=surplus,
                category_breakdown=category_breakdown, tag_breakdown=tag_breakdown,
                waste_items=waste_items, suggestions=suggestions, summary=summary,
            )
            self.session.add(review)

        await self.session.flush()
        return review

    @staticmethod
    def _generate_suggestions(category_breakdown: dict, tag_breakdown: dict, total_spent: float, total_budget: float) -> list[str]:
        """生成省钱建议"""
        suggestions = []

        impulse_total = tag_breakdown.get('impulse', {}).get('total', 0)
        if impulse_total > total_spent * 0.2:
            suggestions.append(f"冲动消费占比高（¥{impulse_total:.0f}），建议大额消费前冷静48小时")

        hoarding_total = tag_breakdown.get('hoarding', {}).get('total', 0)
        if hoarding_total > 0:
            suggestions.append(f"囤货支出¥{hoarding_total:.0f}，建议按需购买避免闲置")

        if total_spent > total_budget:
            suggestions.append(f"本月超支¥{total_spent - total_budget:.0f}，建议下月收紧非必要开支")

        food_total = category_breakdown.get('food', {}).get('total', 0)
        if food_total > total_spent * 0.4:
            suggestions.append(f"餐饮支出占比高（¥{food_total:.0f}），建议增加自制餐比例")

        if not suggestions:
            suggestions.append("消费结构合理，继续保持！")

        return suggestions

    # ==================== 预算提醒 ====================

    async def check_budget_alerts(self, month: str | None = None) -> list[BudgetAlert]:
        """检查预算提醒"""
        if not month:
            month = datetime.utcnow().strftime('%Y-%m')

        # 获取所有预算
        budgets = await self.session.execute(
            select(Budget).where(
                and_(Budget.user_id == self.user_id, Budget.effective_month == month)
            )
        )

        alerts = []
        for budget in budgets.scalars().all():
            # 计算已用
            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(ConsumeRecord.amount), 0)).where(
                    and_(
                        ConsumeRecord.user_id == self.user_id,
                        ConsumeRecord.category == budget.category,
                        func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                    )
                )
            )
            spent = spent_result.scalar() or 0
            percentage = spent / budget.monthly_limit if budget.monthly_limit > 0 else 0

            if percentage >= 0.8:
                if percentage >= 1.0:
                    alert_type = 'exceeded'
                elif percentage >= 0.95:
                    alert_type = 'critical'
                else:
                    alert_type = 'warning'

                # 检查是否已提醒
                existing = await self.session.execute(
                    select(BudgetAlert).where(
                        and_(
                            BudgetAlert.user_id == self.user_id,
                            BudgetAlert.category == budget.category,
                            BudgetAlert.effective_month == month,
                            BudgetAlert.alert_type == alert_type,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                alert = BudgetAlert(
                    user_id=self.user_id,
                    category=budget.category,
                    alert_type=alert_type,
                    current_amount=spent,
                    budget_limit=budget.monthly_limit,
                    percentage=round(percentage, 3),
                )
                self.session.add(alert)
                alerts.append(alert)

        await self.session.flush()
        return alerts

    async def get_active_alerts(self, month: str | None = None) -> list[BudgetAlert]:
        """获取未读提醒"""
        if not month:
            month = datetime.utcnow().strftime('%Y-%m')

        result = await self.session.execute(
            select(BudgetAlert).where(
                and_(
                    BudgetAlert.user_id == self.user_id,
                    BudgetAlert.is_read == False,
                )
            ).order_by(BudgetAlert.created_at.desc())
        )
        return list(result.scalars().all())
