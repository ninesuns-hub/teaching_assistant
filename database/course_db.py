import sqlite3
import os
from config import SQLITE_DB_PATH


def init_db() -> None:
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_info (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT NOT NULL,
            keywords    TEXT NOT NULL,
            question    TEXT NOT NULL,
            answer      TEXT NOT NULL,
            updated_at  TEXT DEFAULT (date('now'))
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM course_info")
    if cursor.fetchone()[0] == 0:
        sample_data = [

            # ── 老师基本信息（Slide 1、2）──────────────────────
            (
                "teacher",
                "老师,教授,魏可佶,老师是谁,教这门课的",
                "授课老师信息",
                "授课老师：魏可佶（Keji Wei），同济大学经管学院运筹学与智能决策研究所 副教授（终身教职）。\n"
                "学术背景：西安交通大学自动化本科，美国达特茅斯学院运筹学博士。\n"
                "曾任职 Sabre 公司研究科学家，从事航空业运筹学研究。"
            ),
            (
                "teacher",
                "邮箱,联系,邮件,email,怎么联系老师",
                "老师联系方式",
                "老师邮箱：kejiwei@tongji.edu.cn\n"
                "个人主页：https://kejiwei.github.io/"
            ),

            # ── 课堂规定（Slide 3）────────────────────────────
            (
                "rule",
                "课堂规定,规则,手机,电脑,laptop,政策,policy",
                "课堂规定",
                "课堂规定（Policy）：\n"
                "• 不允许带笔记本电脑和手机（No Laptop, No cell phones）\n"
                "• 可以用中文或英文回答问题（English or Chinese is okay）\n"
                "• 按时出勤（Attend all classes on time）\n"
                "• 积极回答问题（Answer questions actively）\n"
                "• 考试前解决所有疑问（Solve everything before final exam）\n"
                "• 本课程为英文教学课程"
            ),
            (
                "rule",
                "课程网站,网站,课程主页,网址,官网",
                "课程网站",
                "课程官方网站：https://kejiwei.github.io/teaching/courses/dismath/\n"
                "课程相关资料、通知等请访问该网站获取。"
            ),

            # ── 课程基本信息（Slide 9、10）────────────────────
            (
                "info",
                "课程编号,编号,course number",
                "课程编号",
                "课程编号：01112201"
            ),
            (
                "info",
                "学期,哪个学期,term,spring",
                "开课学期",
                "开课学期：2026年春季学期（2026 Spring）"
            ),
            (
                "info",
                "上课时间,几点上课,课表,时间,class time",
                "上课时间",
                "上课时间：\n"
                "• 周二（Tuesday）10:00 am - 11:35 am\n"
                "• 周四（Thursday）8:00 am - 9:35 am"
            ),
            (
                "info",
                "上课地点,教室,在哪上课,venue,地点",
                "上课地点",
                "上课地点：四平路校区，北教学楼 105 室（Rm 105, North Teaching Bldg, Siping Rd Campus）"
            ),
            (
                "info",
                "答疑,office hour,答疑时间,答疑地点,办公室",
                "答疑时间与地点",
                "答疑时间：每周五下午 2:00 - 4:00 pm（Friday 2-4 pm）\n"
                "答疑地点：同济大学经管学院 A 楼 1229 室（Tongji School of SEM Building A, 1229）"
            ),
            (
                "info",
                "学分,几学分,credit",
                "课程学分",
                "课程学分：4 学分（4 Credits）"
            ),
            (
                "info",
                "课时,学时,几课时,hours",
                "课程学时",
                "课内学时：64 学时"
            ),
            (
                "info",
                "授课语言,语言,英文,中文,language",
                "授课语言",
                "授课语言：英文（English），课程为英文教学，回答问题可使用中文或英文。"
            ),
            (
                "info",
                "课程性质,专业课,基础课,性质",
                "课程性质",
                "课程性质：专业基础课\n"
                "考核方式：考查（非考试）"
            ),
            (
                "info",
                "先修课程,前置课程,需要什么基础,prerequisite",
                "先修课程要求",
                "先修课程：高等数学、线性代数、C 语言程序设计、面向对象程序设计"
            ),

            # ── 评分标准（Slide 14）───────────────────────────
            (
                "grading",
                "评分,成绩,分数,占比,怎么算,grading,平时分，给分标准",
                "课程评分标准",
                "课程评分构成：\n"
                "• 出勤/课堂讨论（Attendance/Discussion）：5%\n"
                "  - 努力出勤，有疑问随时提问\n"
                "• 阶段性测验（Intermediate exams）：35%\n"
                "  - 共 5-10 次课堂测验，每次 5 道题，不允许使用电子设备\n"
                "  - 会去掉最低的一次测验成绩\n"
                "• 期末考试（Final exam）：60%\n"
                "  - 允许携带一张 A4 纸（可记录关键信息）进入考场\n"
                "  - 不允许使用电子设备\n"
                "• 课堂积极参与可获得额外 5% 加分（bonus）"
            ),
            (
                "grading",
                "测验,quiz,小测,阶段考试,intermediate exam",
                "阶段性测验说明",
                "阶段性测验（Intermediate exams）：\n"
                "• 共 5-10 次，在课堂上进行\n"
                "• 每次 5 道题\n"
                "• 不允许使用电子设备\n"
                "• 最终会去掉最低的一次成绩\n"
                "• 合计占总成绩 35%"
            ),
            (
                "grading",
                "期末,期末考试,final exam,期末考试规定",
                "期末考试规定",
                "期末考试（Final exam）：\n"
                "• 占总成绩 60%\n"
                "• 允许携带一张 A4 纸进入考场（可提前记录关键信息）\n"
                "• 不允许使用任何电子设备\n"
                "• 具体考试时间和地点请关注课程网站：https://kejiwei.github.io/teaching/courses/dismath/"
            ),

            # ── 章节与课时安排（Slide 13）─────────────────────
            (
                "schedule",
                "章节,课时安排,教学内容,讲什么,知识点,syllabus",
                "课程章节与课时安排",
                "课程章节与课时安排：\n"
                "• 集合论与证明方法（Set Theory and Proof Methods）：6 课时\n"
                "• 命题逻辑（Propositional Logic）：6 课时\n"
                "• 一阶逻辑（First-Order Logic）：5 课时\n"
                "• 关系（Relations）：6 课时\n"
                "• 函数（Functions）：6 课时\n"
                "• 图论（Graphs）：7 课时\n"
                "• 树及其应用（Trees and Their Applications）：5 课时\n"
                "• 初等数论（Elementary Number Theory）：4 课时\n"
                "• 代数系统·群论（Algebraic Systems - Group Theory）：14 课时\n"
                "• 综合复习（Comprehensive Review）：2 课时\n"
                "• 合计：64 课时"
            ),

            # ── 参考书目（Slide 15）───────────────────────────
            (
                "resource",
                "参考书,教材,书,textbook,reference,推荐书目",
                "课程参考书目",
                "课程参考书目：\n"
                "① 离散数学 / 耿素云、曲婉玲、张立昂 著\n"
                "   清华大学出版社，2021，第6版，ISBN: 9787302592686\n\n"
                "② Discrete Mathematics and Its Applications / Kenneth H. Rosen\n"
                "   McGraw-Hill，2019，第8版，ISBN: 978125967651\n\n"
                "③ 离散数学及其应用（中译版）/ Kenneth H. Rosen 著，徐六通等译\n"
                "   机械工业出版社，2019，第8版，ISBN: 9787111636878"
            ),

            # ── 学习建议（Slide 16、17）───────────────────────
            (
                "advice",
                "建议,学习建议,如何学好,怎么学,技巧,suggestion",
                "课程学习建议",
                "课程学习建议（Suggestion）：\n"
                "• 从教材中做额外练习题（Solve additional exercises from text books）\n"
                "• 提前预习课程内容（Prepare lesson content in advance）\n"
                "• 独立思考并完成测验（Think and finish exams independently）\n"
                "• 充分利用助教和老师资源（Fully utilize TA/Instructor resources）\n"
                "• 不要投机取巧（No tricks，如弃考、拖延等）\n"
                "• 课程网站：https://kejiwei.github.io/teaching/courses/dismath/"
            ),

            # ── 课程目标（Slide 11、12）───────────────────────
            (
                "objective",
                "课程目标,教学目标,学什么,学习目标,objective",
                "课程教学目标",
                "课程教学目标：\n"
                "目标1：熟练掌握集合论基本概念、基本理论和证明方法\n"
                "目标2：理解数理逻辑（命题逻辑和一阶逻辑）基本概念和理论，学会应用\n"
                "目标3：熟练掌握关系与函数的基本概念和理论，能用相关方法分析解决问题\n"
                "目标4：熟练掌握图论（含树）基本概念和理论，能用图论模型分析解决问题\n"
                "目标5：熟练掌握抽象代数基本概念和理论，能用相关方法分析解决问题"
            ),
        ]

        cursor.executemany(
            "INSERT INTO course_info (category, keywords, question, answer) VALUES (?, ?, ?, ?)",
            sample_data
        )
        print("[SQLite] 课程数据初始化完成，共写入", len(sample_data), "条记录")

    conn.commit()
    conn.close()


def query_course_admin(user_question: str) -> str | None:
    """
    返回所有命中的课程信息，合并后一起返回。
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT keywords, answer FROM course_info")
    rows = cursor.fetchall()
    conn.close()

    matched = []

    for keywords_str, answer in rows:
        keywords = [kw.strip() for kw in keywords_str.split(",")]

        hit_count = 0
        max_kw_len = 0
        for kw in keywords:
            if kw and kw in user_question:
                hit_count += 1
                max_kw_len = max(max_kw_len, len(kw))

        if hit_count > 0:
            matched.append((hit_count, max_kw_len, answer))

    if not matched:
        return None

    # 按命中数降序、关键词长度降序排列
    matched.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # 如果只命中一条，直接返回
    if len(matched) == 1:
        return matched[0][2]

    # 命中多条时，合并返回
    combined = "\n\n---\n\n".join(item[2] for item in matched)
    return combined