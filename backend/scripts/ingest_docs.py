import sys
import os
import logging

# 确保可以导入 backend 目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.core.data_manager import data_manager
from agent_core.config.settings import settings

def main():
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("IngestionScript")

    logger.info("开始执行命令行文档入库工具...")

    # 直接调用 DataManager 的逻辑，确保与 Web 端行为一致
    files = data_manager.get_all_course_files()
    if not files:
        logger.warning(f"目录 {settings.COURSE_ASSETS_DIR} 中未发现可处理的文件。")
        return

    for filename in files:
        file_path = os.path.join(settings.COURSE_ASSETS_DIR, filename)
        logger.info(f"正在入库: {filename}")
        data_manager.ingest_file(file_path)

    logger.info("所有文档处理完成！")

if __name__ == "__main__":
    main()
