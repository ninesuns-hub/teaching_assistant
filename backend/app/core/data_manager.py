import os
import shutil
import logging
from typing import List, Dict, Any
from agent_core.config.settings import settings
from agent_core.rag.processor import DocumentProcessor
from agent_core.rag.retriever import HybridSearcher

logger = logging.getLogger(__name__)

class DataManager:
    """
    缁熶竴鏁版嵁绠＄悊绯荤粺
    鑱岃矗锛氭枃浠剁綉鍏炽€丷AG 鑷姩瑙﹀彂銆侀殧绂诲瓨鍌ㄧ鐞?
    """
    def __init__(self):
        self.processor = DocumentProcessor()
        self.searcher = HybridSearcher()
        self._ensure_dirs()

    def _ensure_dirs(self):
        """纭繚鎵€鏈夊瓨鍌ㄧ洰褰曞瓨鍦?""
        dirs = [
            settings.COURSE_ASSETS_DIR,
            settings.CHUNKS_DIR,
            os.path.dirname(settings.SQLITE_DB_PATH),
            os.path.dirname(settings.LOG_FILE)
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def save_course_file(self, file_content: bytes, filename: str, auto_ingest: bool = True):
        """
        淇濆瓨璇剧▼鐩稿叧鏂囦欢骞跺彲閫夎嚜鍔ㄨЕ鍙?RAG
        """
        target_path = os.path.join(settings.COURSE_ASSETS_DIR, filename)
        try:
            with open(target_path, "wb") as f:
                f.write(file_content)
            logger.info(f"鏂囦欢宸蹭繚瀛樿嚦: {target_path}")

            if auto_ingest:
                self.ingest_file(target_path)

            return {"status": "success", "path": target_path}
        except Exception as e:
            logger.error(f"淇濆瓨鏂囦欢澶辫触: {e}")
            return {"status": "error", "message": str(e)}

    def ingest_file(self, file_path: str):
        """
        鎵嬪姩瑙﹀彂鍗曚釜鏂囦欢鐨?RAG 鍏ュ簱
        """
        logger.info(f"寮€濮嬪鐞嗘枃浠跺叆搴? {file_path}")
        ext = file_path.lower()
        chunks = []

        if ext.endswith((".pptx", ".ppsx")):
            chunks = self.processor.pptx_parser.parse(file_path)
        elif ext.endswith(".pdf"):
            chunks = self.processor.pdf_parser.parse(file_path)
        else:
            logger.warning(f"鏆備笉鏀寔鐨勬枃浠舵牸寮? {file_path}")
            return

        if chunks:
            self.searcher.add_documents(chunks)
            logger.info(f"鏂囦欢 {file_path} 宸叉垚鍔熼泦鎴愯嚦 RAG 绯荤粺")
        else:
            logger.warning(f"鏂囦欢 {file_path} 瑙ｆ瀽缁撴灉涓虹┖")

    def get_all_course_files(self) -> List[str]:
        """鑾峰彇鎵€鏈夊凡涓婁紶鐨勮绋嬫枃浠跺垪琛?""
        if not os.path.exists(settings.COURSE_ASSETS_DIR):
            return []
        return os.listdir(settings.COURSE_ASSETS_DIR)

    def delete_course_file(self, filename: str):
        """鍒犻櫎璇剧▼鏂囦欢锛堟敞鎰忥細鐩墠鏈疄鐜颁粠鍚戦噺搴撲腑鍗曚釜鍒犻櫎锛?""
        target_path = os.path.join(settings.COURSE_ASSETS_DIR, filename)
        if os.path.exists(target_path):
            os.remove(target_path)
            logger.info(f"宸插垹闄ゆ枃浠? {target_path}")
            return True
        return False

    def clear_all_data(self):
        """
        娓呯┖鎵€鏈夊凡鍏ュ簱鐨勬暟鎹储寮?
        """
        self.searcher.clear_all()
        # 鍚屾椂娓呯悊澶勭悊鍚庣殑涓棿鏂囦欢
        if os.path.exists(settings.CHUNKS_DIR):
            for f in os.listdir(settings.CHUNKS_DIR):
                if f.endswith(".md") or f.endswith(".json"):
                    os.remove(os.path.join(settings.CHUNKS_DIR, f))
        logger.info("鎵€鏈夋湰鍦扮紦瀛樺拰绱㈠紩宸叉竻鐞嗗畬姣?)

# 鍏ㄥ眬鍗曚緥
data_manager = DataManager()
