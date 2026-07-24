import os
import shutil
import logging
import uuid
from typing import List, Dict, Any
from agent_core.config.settings import settings
from agent_core.rag.processor import DocumentProcessor
from agent_core.rag.retriever import HybridSearcher

logger = logging.getLogger(__name__)

class DataManager:
    """
    统一数据管理系统
    职责：文件网关、RAG 自动触发、隔离存储管理
    """
    def __init__(self):
        self.processor = DocumentProcessor()
        self.searcher = HybridSearcher()
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保所有存储目录存在"""
        dirs = [
            settings.COURSE_ASSETS_DIR,
            settings.CLASS_MATERIALS_DIR,
            settings.HOMEWORK_DIR,
            settings.CHUNKS_DIR,
            os.path.dirname(settings.SQLITE_DB_PATH),
            os.path.dirname(settings.LOG_FILE)
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def save_course_file(self, file_content: bytes, filename: str, auto_ingest: bool = True):
        """
        保存课程相关文件并可选自动触发 RAG
        """
        target_path = os.path.join(settings.COURSE_ASSETS_DIR, filename)
        try:
            with open(target_path, "wb") as f:
                f.write(file_content)
            logger.info(f"文件已保存至: {target_path}")

            if auto_ingest:
                self.ingest_file(target_path)

            return {"status": "success", "path": target_path}
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return {"status": "error", "message": str(e)}

    def save_class_material(self, file_content: bytes, filename: str, class_id: int, auto_ingest: bool = True):
        """保存班级学习资料并触发 RAG 入库"""
        class_dir = os.path.join(settings.CLASS_MATERIALS_DIR, str(class_id))
        os.makedirs(class_dir, exist_ok=True)
        target_path = os.path.join(class_dir, filename)
        try:
            with open(target_path, "wb") as f:
                f.write(file_content)
            logger.info(f"班级资料已保存至: {target_path}")
            if auto_ingest:
                self.ingest_file(target_path)
            return {"status": "success", "path": target_path}
        except Exception as e:
            logger.error(f"保存班级资料失败: {e}")
            return {"status": "error", "message": str(e)}

    def save_homework_file(
        self,
        file_content: bytes,
        filename: str,
        class_id: int,
        kind: str = "assignment",
        homework_id: int | None = None,
        student_id: int | None = None,
    ):
        """保存作业附件或学生提交文件（不入库 RAG）"""
        parts = [settings.HOMEWORK_DIR, str(class_id)]
        if kind == "submission" and homework_id is not None:
            parts.extend(["submissions", str(homework_id)])
            if student_id is not None:
                parts.append(str(student_id))
        else:
            parts.append("assignments")
        target_dir = os.path.join(*parts)
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, filename)
        try:
            with open(target_path, "wb") as f:
                f.write(file_content)
            logger.info(f"作业文件已保存至: {target_path}")
            return {"status": "success", "path": target_path}
        except Exception as e:
            logger.error(f"保存作业文件失败: {e}")
            return {"status": "error", "message": str(e)}

    def save_homework_attachment(
        self,
        file_content: bytes,
        filename: str,
        class_id: int,
        homework_id: int,
    ):
        """使用唯一物理文件名保存作业附件，同时保留原始展示名称。"""
        target_dir = os.path.join(
            settings.HOMEWORK_DIR,
            str(class_id),
            "assignments",
            str(homework_id),
        )
        os.makedirs(target_dir, exist_ok=True)
        safe_name = os.path.basename(filename)
        ext = os.path.splitext(safe_name)[1].lower()
        target_path = os.path.join(target_dir, f"{uuid.uuid4().hex}{ext}")
        try:
            with open(target_path, "wb") as file_obj:
                file_obj.write(file_content)
            return {"status": "success", "path": target_path}
        except Exception as exc:
            logger.error("保存作业附件失败: %s", exc)
            return {"status": "error", "message": str(exc)}

    def ingest_file(self, file_path: str, metadata: Dict[str, Any] | None = None):
        """
        手动触发单个文件的 RAG 入库
        """
        logger.info(f"开始处理文件入库: {file_path}")
        ext = file_path.lower()
        chunks = []
        artifact_name = None
        if metadata and metadata.get("source_key"):
            artifact_name = str(metadata["source_key"]).replace(":", "_")

        if ext.endswith((".pptx", ".ppsx")):
            chunks = self.processor.pptx_parser.parse(file_path, artifact_name=artifact_name)
        elif ext.endswith(".pdf"):
            chunks = self.processor.pdf_parser.parse(file_path, artifact_name=artifact_name)
        else:
            logger.warning(f"暂不支持的文件格式: {file_path}")
            return

        if chunks:
            if metadata:
                for chunk in chunks:
                    chunk["metadata"] = {
                        **chunk.get("metadata", {}),
                        **metadata,
                    }
            self.searcher.add_documents(chunks)
            logger.info(f"文件 {file_path} 已成功集成至 RAG 系统")
        else:
            logger.warning(f"文件 {file_path} 解析结果为空")

    def delete_class_material_index(self, class_id: int, material_id: int):
        """删除指定班级资料在向量与关键词检索中的内容。"""
        self.searcher.delete_material_documents(class_id, material_id)
        artifact_path = os.path.join(
            settings.CHUNKS_DIR,
            f"class_{class_id}_material_{material_id}.md",
        )
        if os.path.isfile(artifact_path):
            os.remove(artifact_path)

    def get_all_course_files(self) -> List[str]:
        """获取所有已上传的课程文件列表"""
        if not os.path.exists(settings.COURSE_ASSETS_DIR):
            return []
        return os.listdir(settings.COURSE_ASSETS_DIR)

    def delete_course_file(self, filename: str):
        """删除课程文件（注意：目前未实现从向量库中单个删除）"""
        target_path = os.path.join(settings.COURSE_ASSETS_DIR, filename)
        if os.path.exists(target_path):
            os.remove(target_path)
            logger.info(f"已删除文件: {target_path}")
            return True
        return False

    def clear_all_data(self):
        """
        清空所有已入库的数据索引
        """
        self.searcher.clear_all()
        # 同时清理处理后的中间文件
        if os.path.exists(settings.CHUNKS_DIR):
            for f in os.listdir(settings.CHUNKS_DIR):
                if f.endswith(".md") or f.endswith(".json"):
                    os.remove(os.path.join(settings.CHUNKS_DIR, f))
        logger.info("所有本地缓存和索引已清理完毕")

# 全局单例
data_manager = DataManager()
