# -*- coding: utf-8 -*-
"""
数据层：SQLite 本地存储血压记录
所有健康数据仅保存在本地，不上传云端。
"""

import os
import sqlite3
import csv
from datetime import datetime, timedelta


class BPDB:
    """血压记录数据库管理类"""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bp.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS bp_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                measure_time TEXT NOT NULL,
                systolic INTEGER NOT NULL,
                diastolic INTEGER NOT NULL,
                pulse INTEGER NOT NULL,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        ''')
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_measure_time ON bp_records(measure_time)
        ''')
        self.conn.commit()

    # ---------------- 行转换 ----------------
    @staticmethod
    def _d(row):
        return dict(row) if row is not None else None

    def _ds(self, rows):
        return [dict(r) for r in rows]

    # ---------------- 增 ----------------
    def add_record(self, measure_time, systolic, diastolic, pulse, note=''):
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur = self.conn.execute(
            'INSERT INTO bp_records (measure_time, systolic, diastolic, pulse, note, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (measure_time, int(systolic), int(diastolic), int(pulse), note or '', created_at)
        )
        self.conn.commit()
        return cur.lastrowid

    # ---------------- 查 ----------------
    def get_all(self):
        return self._ds(self.conn.execute(
            'SELECT * FROM bp_records ORDER BY measure_time DESC, id DESC'
        ).fetchall())

    def get_by_id(self, rid):
        return self._d(self.conn.execute(
            'SELECT * FROM bp_records WHERE id = ?', (rid,)).fetchone())

    def get_recent(self, limit=50):
        return self._ds(self.conn.execute(
            'SELECT * FROM bp_records ORDER BY measure_time DESC, id DESC LIMIT ?',
            (int(limit),)
        ).fetchall())

    def query_by_date(self, date_str):
        """date_str: YYYY-MM-DD 或 YYYY-MM 或 YYYY"""
        return self._ds(self.conn.execute(
            'SELECT * FROM bp_records WHERE measure_time LIKE ? ORDER BY measure_time DESC',
            (date_str + '%',)
        ).fetchall())

    def query_range(self, start_date, end_date):
        """start_date / end_date: YYYY-MM-DD"""
        return self._ds(self.conn.execute(
            'SELECT * FROM bp_records WHERE measure_time >= ? AND measure_time < ? '
            'ORDER BY measure_time DESC',
            (start_date, end_date)
        ).fetchall())

    def search(self, keyword):
        return self._ds(self.conn.execute(
            'SELECT * FROM bp_records WHERE note LIKE ? ORDER BY measure_time DESC',
            ('%' + keyword + '%',)
        ).fetchall())

    # ---------------- 改 ----------------
    def update_record(self, rid, measure_time, systolic, diastolic, pulse, note=''):
        self.conn.execute(
            'UPDATE bp_records SET measure_time=?, systolic=?, diastolic=?, pulse=?, note=? WHERE id=?',
            (measure_time, int(systolic), int(diastolic), int(pulse), note or '', int(rid))
        )
        self.conn.commit()

    # ---------------- 删 ----------------
    def delete_record(self, rid):
        self.conn.execute('DELETE FROM bp_records WHERE id = ?', (int(rid),))
        self.conn.commit()

    def delete_all(self):
        self.conn.execute('DELETE FROM bp_records')
        self.conn.commit()

    # ---------------- 统计 ----------------
    def get_stats(self, days=30):
        """返回最近 N 天的统计：avg/max/min of 高压/低压/脉搏"""
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        row = self.conn.execute(
            'SELECT '
            'AVG(systolic) AS sys_avg, MAX(systolic) AS sys_max, MIN(systolic) AS sys_min, '
            'AVG(diastolic) AS dia_avg, MAX(diastolic) AS dia_max, MIN(diastolic) AS dia_min, '
            'AVG(pulse) AS pul_avg, MAX(pulse) AS pul_max, MIN(pulse) AS pul_min, '
            'COUNT(*) AS cnt '
            'FROM bp_records WHERE measure_time >= ?',
            (start,)
        ).fetchone()
        return self._d(row)

    def get_daily_summary(self, days=7):
        """按天汇总最近 N 天"""
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        return self._ds(self.conn.execute(
            'SELECT substr(measure_time, 1, 10) AS d, '
            'COUNT(*) AS cnt, '
            'ROUND(AVG(systolic),1) AS sys_avg, '
            'ROUND(AVG(diastolic),1) AS dia_avg, '
            'ROUND(AVG(pulse),1) AS pul_avg '
            'FROM bp_records WHERE measure_time >= ? '
            'GROUP BY d ORDER BY d DESC',
            (start,)
        ).fetchall())

    def get_monthly_summary(self, months=6):
        start = (datetime.now() - timedelta(days=30 * months)).strftime('%Y-%m')
        return self._ds(self.conn.execute(
            'SELECT substr(measure_time, 1, 7) AS m, '
            'COUNT(*) AS cnt, '
            'ROUND(AVG(systolic),1) AS sys_avg, '
            'ROUND(AVG(diastolic),1) AS dia_avg, '
            'ROUND(AVG(pulse),1) AS pul_avg '
            'FROM bp_records WHERE measure_time >= ? '
            'GROUP BY m ORDER BY m DESC',
            (start,)
        ).fetchall())

    # ---------------- 导出 / 备份 ----------------
    def export_csv(self, path):
        rows = self.get_all()
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', '测量时间', '高压(mmHg)', '低压(mmHg)', '脉搏(次/分)', '备注'])
            for r in rows:
                writer.writerow([r['id'], r['measure_time'], r['systolic'],
                                 r['diastolic'], r['pulse'], r['note']])
        return path

    def backup_db(self, backup_dir=None):
        """本地备份数据库文件"""
        if backup_dir is None:
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        dst = os.path.join(backup_dir, f'bp_backup_{ts}.db')
        self.conn.commit()
        with open(self.db_path, 'rb') as src, open(dst, 'wb') as out:
            out.write(src.read())
        return dst

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
