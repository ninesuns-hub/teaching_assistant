import sys
import os
import logging

# 确保可以导入 backend 目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from agent_core.rag import DocumentProcessor, HybridSearcher
from agent_core.config.settings import settings

def main():
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("IngestionScript")

    logger.info("开始文档入库流程...")

    # 1. 初始化处理器和检索器
    processor = DocumentProcessor()
    searcher = HybridSearcher()

    # 2. 解析目录中的所有 PPTX
    logger.info(f"正在扫描目录: {settings.RAW_DATA_DIR}")
    chunks = processor.process_directory(settings.RAW_DATA_DIR)

    if not chunks:
        logger.warning("未发现可处理的文档或解析结果为空。")
        return

    logger.info(f"解析完成，共获得 {len(chunks)} 个文本块。")

    # 3. 写入混合检索系统 (Qdrant + BM25)
    logger.info("正在将数据写入 Qdrant 和 BM25 索引...")
    try:
        searcher.add_documents(chunks)
        logger.info("数据入库成功！")
    except Exception as e:
        logger.error(f"数据入库失败: {e}")

    logger.info(f"处理完成。你可以查看 {settings.PROCESSED_DATA_DIR} 目录下的 Markdown 文件进行调试。")

if __name__ == "__main__":
    main()
