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

import argparse

def main():
    parser = argparse.ArgumentParser(description="离散数学 RAG 文档入库/重录工具")
    parser.add_argument("--clear", action="store_true", help="在入库前清空现有的所有索引")
    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("IngestionScript")

    if args.clear:
        logger.info("检测到 --clear 参数，正在清空现有索引...")
        data_manager.clear_all_data()

    logger.info("开始执行文档入库...")

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
