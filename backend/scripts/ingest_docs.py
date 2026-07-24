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
from database import rag_repo
from database.mysql_db import SessionLocal, init_mysql

import argparse


def register_and_index(
    db,
    file_path: str,
    filename: str,
    scope_type: str,
    class_id: int | None = None,
    material=None,
):
    logger = logging.getLogger("IngestionScript")
    content_hash = data_manager.calculate_file_hash(file_path)
    file_type = os.path.splitext(filename)[1].lower().lstrip(".")
    file_size = os.path.getsize(file_path)

    if material is not None and material.content_hash != content_hash:
        material.content_hash = content_hash
        db.commit()

    document, _ = rag_repo.get_or_create_document(
        db,
        content_hash=content_hash,
        file_type=file_type,
        file_size=file_size,
    )
    rag_repo.add_source(
        db,
        document_id=document.id,
        scope_type=scope_type,
        class_id=class_id,
        material_id=material.id if material is not None else None,
        filename=filename,
        file_path=file_path,
    )
    sources = rag_repo.list_sources(db, document.id)
    scope_keys = rag_repo.scope_keys(sources)
    serialized_sources = rag_repo.serialize_sources(sources)

    if document.index_status == "ready":
        data_manager.update_document_access(
            content_hash, scope_keys, serialized_sources
        )
        logger.info("复用内容索引: %s", filename)
        return

    try:
        indexed = data_manager.ingest_file(
            file_path,
            metadata={
                "document_hash": content_hash,
                "scope_keys": scope_keys,
                "sources": serialized_sources,
                "source_key": f"document:{content_hash}",
            },
        )
        if not indexed:
            raise RuntimeError("未提取到可索引文本")
        rag_repo.set_document_status(db, document, "ready")
    except Exception:
        rag_repo.set_document_status(db, document, "failed")
        raise

def main():
    parser = argparse.ArgumentParser(description="离散数学 RAG 文档入库/重录工具")
    parser.add_argument("--clear", action="store_true", help="兼容参数：等同于 --rebuild-scoped")
    parser.add_argument(
        "--rebuild-scoped",
        action="store_true",
        help="清空旧索引并按文件哈希重建公共及班级作用域索引",
    )
    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("IngestionScript")

    init_mysql()
    rebuild = args.clear or args.rebuild_scoped
    db = SessionLocal()

    if rebuild:
        logger.info("正在清空旧索引和哈希来源登记...")
        data_manager.clear_all_data()
        rag_repo.clear_registry(db)

    try:
        logger.info("开始登记公共课程资料...")
        for filename in data_manager.get_all_course_files():
            file_path = os.path.realpath(
                os.path.join(settings.COURSE_ASSETS_DIR, filename)
            )
            if not os.path.isfile(file_path):
                continue
            register_and_index(
                db,
                file_path=file_path,
                filename=filename,
                scope_type="global",
            )

        logger.info("开始登记班级学习资料...")
        for material in rag_repo.list_all_class_materials(db):
            file_path = os.path.realpath(material.file_path)
            if not os.path.isfile(file_path):
                logger.warning("班级资料文件缺失，跳过: %s", material.filename)
                continue
            register_and_index(
                db,
                file_path=file_path,
                filename=material.filename,
                scope_type="class",
                class_id=material.class_id,
                material=material,
            )
        logger.info("公共与班级作用域索引处理完成！")
    finally:
        db.close()

if __name__ == "__main__":
    main()
