# author: delta1037
# Date: 2022/05/01
# mail:geniusrabbit@qq.com
# 终端-打包代码 pyinstaller -F -c -i notion-dump.ico notion_backup_terminal.py -p api/notion_dump.py -p api/notion_dump_api.py -p api/backup_info.py
# 终端-打包代码 pyinstaller notion_backup_terminal.spec
# 后台-打包代码 pyinstaller -F -i notion-dump.ico notion_backup_terminal.py -p api/notion_dump.py -p api/notion_dump_api.py -p api/backup_info.py
# 后台-打包代码 pyinstaller notion_backup_background.spec
import os
import sys
import time
import traceback

from NotionDump import NotionBackupLogger

from api.notion_dump import NotionBackup

SEVER_ABS_PATH = os.path.dirname(sys.argv[0])
# 摘要日志：每次备份只追加关键信息，长期保留
LOG_FILE = SEVER_ABS_PATH + "/dump.log"
# 详细日志：每次备份一个文件，只保留最近几次
DETAIL_LOG_DIR = SEVER_ABS_PATH + "/logs"
DETAIL_LOG_KEEP = 3
# 写入摘要日志的关键信息
SUMMARY_KEYS = ("start backup", "server version", "kernel version", "page_id:", "prefetch page edit time",
                "page dump end", "pages with the same name", "sync to", "kernel dump error list",
                "backup success", "backup fail", "备份成功", "部分备份失败", "没有需要备份的内容",
                "Config init failed", "token is null", "_id is null", "param check fail", "page dump fail",
                "main page:", "unknown dump type", "unknown type")


class Logger(NotionBackupLogger):
    def __init__(self):
        super().__init__()
        self.terminal = sys.stdout
        self.start_time = time.time()
        self.__summary_next = False
        if not os.path.exists(DETAIL_LOG_DIR):
            os.makedirs(DETAIL_LOG_DIR)
        # 删除较早的详细日志
        old_logs = sorted(f for f in os.listdir(DETAIL_LOG_DIR) if f.startswith("dump_") and f.endswith(".log"))
        for old_log in old_logs[0:max(len(old_logs) - DETAIL_LOG_KEEP + 1, 0)]:
            os.remove(DETAIL_LOG_DIR + "/" + old_log)
        detail_name = DETAIL_LOG_DIR + time.strftime("/dump_%Y%m%d_%H%M%S.log", time.localtime(self.start_time))
        self.__log = open(detail_name, "a+", encoding='utf-8')
        self.__summary = open(LOG_FILE, "a+", encoding='utf-8')
        # 输出备份的时间
        backup_time = time.strftime('backup_time: %Y-%m-%d %H:%M:%S\n', time.localtime(self.start_time))
        if self.terminal is not None:
            self.terminal.write(backup_time)
        for fd in (self.__log, self.__summary):
            fd.write("\n###################################################\n")
            fd.write(backup_time)
            fd.flush()
        self.__summary.write("detail log: " + detail_name + "\n")
        self.__summary.flush()

    def log_debug(self, log_str):
        self.log_info(log_str)

    def log_info(self, message):
        self.log("[EXPORT KERNEL] " + str(message))

    def log(self, message):
        if self.terminal is not None:
            self.terminal.write(message + "\n")
        self.__log.write(message + "\n")
        self.__log.flush()
        # 关键信息同时写入摘要日志（错误列表在提示的下一行）
        if self.__summary_next or any(key in message for key in SUMMARY_KEYS):
            self.__summary.write(message + "\n")
            self.__summary.flush()
            self.__summary_next = "kernel dump error list" in message

    def finish(self, error=None):
        if error is not None:
            self.log("[EXPORT CLIENT] backup fail with exception:\n" + error)
        self.__summary.write("elapsed: " + str(int(time.time() - self.start_time)) + "s\n")
        self.__summary.flush()

    def flush(self):
        pass


if __name__ == '__main__':
    logger = Logger()
    # 开始备份
    try:
        notion_back = NotionBackup(logger=logger)
        notion_back.start_dump()
    except Exception:
        # 后台运行时没有控制台，异常信息写入日志后退出
        logger.finish(traceback.format_exc())
        sys.exit(1)
    logger.finish()
