"""本地启动脚本（使用h11协议避免httptools的POST解析问题）"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False, http="h11")
