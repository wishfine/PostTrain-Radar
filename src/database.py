import os
import sqlite3
import json
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="data/posttrain_radar.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.run_migrations()

    def run_migrations(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(papers)")
        papers_cols = [row["name"] for row in cursor.fetchall()]
        if "data_origin" not in papers_cols:
            self.conn.execute("ALTER TABLE papers ADD COLUMN data_origin TEXT DEFAULT 'openreview_api'")
            self.conn.commit()
        if "siyuan_sync_time" not in papers_cols:
            self.conn.execute("ALTER TABLE papers ADD COLUMN siyuan_sync_time TEXT")
            self.conn.commit()
        if "siyuan_sync_mode" not in papers_cols:
            self.conn.execute("ALTER TABLE papers ADD COLUMN siyuan_sync_mode TEXT")
            self.conn.commit()

        cursor.execute("PRAGMA table_info(paper_tags)")
        tags_cols = [row["name"] for row in cursor.fetchall()]
        if "matched_evidence" not in tags_cols:
            self.conn.execute("ALTER TABLE paper_tags ADD COLUMN matched_evidence TEXT")
            self.conn.commit()
        if "relevance_level" not in tags_cols:
            self.conn.execute("ALTER TABLE paper_tags ADD COLUMN relevance_level TEXT")
            self.conn.commit()
        if "is_core_posttraining" not in tags_cols:
            self.conn.execute("ALTER TABLE paper_tags ADD COLUMN is_core_posttraining INTEGER DEFAULT 0")
            self.conn.commit()
        if "include_in_reading_queue" not in tags_cols:
            self.conn.execute("ALTER TABLE paper_tags ADD COLUMN include_in_reading_queue INTEGER DEFAULT 0")
            self.conn.commit()
        if "include_in_knowledge_patches" not in tags_cols:
            self.conn.execute("ALTER TABLE paper_tags ADD COLUMN include_in_knowledge_patches INTEGER DEFAULT 0")
            self.conn.commit()
        if "include_in_share_pool" not in tags_cols:
            self.conn.execute("ALTER TABLE paper_tags ADD COLUMN include_in_share_pool INTEGER DEFAULT 0")
            self.conn.commit()
        if "reviewer_comment" not in tags_cols:
            self.conn.execute("ALTER TABLE paper_tags ADD COLUMN reviewer_comment TEXT")
            self.conn.commit()

    def create_tables(self):
        with self.conn:
            # papers table
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                title_norm TEXT NOT NULL,
                abstract TEXT,
                abstract_hash TEXT,
                authors TEXT,
                venue TEXT,
                year INTEGER,
                paper_url TEXT,
                pdf_url TEXT,
                source TEXT,
                source_id TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                siyuan_doc_id TEXT,
                siyuan_path TEXT,
                data_origin TEXT DEFAULT 'openreview_api',
                siyuan_sync_time TEXT,
                siyuan_sync_mode TEXT,
                UNIQUE(source, source_id)
            );
            """)
            
            # paper_tags table
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER,
                is_candidate INTEGER,
                is_relevant INTEGER,
                model_type TEXT,
                post_training_types TEXT, -- JSON array string
                problem_tags TEXT, -- JSON array string
                keywords_matched TEXT, -- JSON array string
                confidence REAL,
                reason TEXT,
                classified_at TEXT,
                reading_status TEXT DEFAULT 'Unread',
                priority TEXT DEFAULT 'Medium',
                share_status TEXT DEFAULT 'Not Started',
                my_rating TEXT,
                next_action TEXT,
                matched_evidence TEXT,
                relevance_level TEXT,
                is_core_posttraining INTEGER DEFAULT 0,
                include_in_reading_queue INTEGER DEFAULT 0,
                include_in_knowledge_patches INTEGER DEFAULT 0,
                include_in_share_pool INTEGER DEFAULT 0,
                reviewer_comment TEXT,
                FOREIGN KEY(paper_id) REFERENCES papers(id)
            );
            """)

            # runs table
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                venue TEXT,
                year INTEGER,
                total_count INTEGER,
                candidate_count INTEGER,
                relevant_count INTEGER,
                run_time TEXT
            );
            """)

    def insert_or_update_paper(self, paper_data):
        """
        Inserts a paper or updates its details if it already exists (by source and source_id).
        Returns the database ID of the paper.
        """
        now = datetime.now().isoformat()
        
        # Check if already exists
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, first_seen_at FROM papers WHERE source = ? AND source_id = ?",
            (paper_data["source"], paper_data["source_id"])
        )
        row = cursor.fetchone()

        data_origin = paper_data.get("data_origin", "openreview_api")

        if row:
            paper_id = row["id"]
            
            self.conn.execute("""
                UPDATE papers SET
                    title = ?,
                    title_norm = ?,
                    abstract = ?,
                    abstract_hash = ?,
                    authors = ?,
                    venue = ?,
                    year = ?,
                    paper_url = ?,
                    pdf_url = ?,
                    status = ?,
                    updated_at = ?,
                    last_seen_at = ?,
                    data_origin = ?
                WHERE id = ?
            """, (
                paper_data["title"],
                paper_data["title_norm"],
                paper_data.get("abstract", ""),
                paper_data.get("abstract_hash", ""),
                json.dumps(paper_data.get("authors", [])),
                paper_data["venue"],
                paper_data["year"],
                paper_data.get("paper_url", ""),
                paper_data.get("pdf_url", ""),
                paper_data.get("status", "accepted"),
                now,
                now,
                data_origin,
                paper_id
            ))
            self.conn.commit()
            return paper_id
        else:
            cursor.execute("""
                INSERT INTO papers (
                    title, title_norm, abstract, abstract_hash, authors, venue, year,
                    paper_url, pdf_url, source, source_id, status, created_at, updated_at,
                    first_seen_at, last_seen_at, data_origin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_data["title"],
                paper_data["title_norm"],
                paper_data.get("abstract", ""),
                paper_data.get("abstract_hash", ""),
                json.dumps(paper_data.get("authors", [])),
                paper_data["venue"],
                paper_data["year"],
                paper_data.get("paper_url", ""),
                paper_data.get("pdf_url", ""),
                paper_data["source"],
                paper_data["source_id"],
                paper_data.get("status", "accepted"),
                now,
                now,
                now,
                now,
                data_origin
            ))
            self.conn.commit()
            return cursor.lastrowid

    def update_paper_tags(self, paper_id, tag_data):
        """
        Inserts or updates the classification tags for a given paper.
        """
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM paper_tags WHERE paper_id = ?", (paper_id,))
        row = cursor.fetchone()

        post_training_types_str = json.dumps(tag_data.get("post_training_types", []))
        problem_tags_str = json.dumps(tag_data.get("problem_tags", []))
        keywords_matched_str = json.dumps(tag_data.get("keywords_matched", []))
        matched_evidence_str = json.dumps(tag_data.get("matched_evidence", {}))

        if row:
            tag_id = row["id"]
            self.conn.execute("""
                UPDATE paper_tags SET
                    is_candidate = ?,
                    is_relevant = ?,
                    model_type = ?,
                    post_training_types = ?,
                    problem_tags = ?,
                    keywords_matched = ?,
                    confidence = ?,
                    reason = ?,
                    classified_at = ?,
                    reading_status = COALESCE(?, reading_status),
                    priority = COALESCE(?, priority),
                    share_status = COALESCE(?, share_status),
                    my_rating = COALESCE(?, my_rating),
                    next_action = COALESCE(?, next_action),
                    matched_evidence = ?,
                    relevance_level = COALESCE(?, relevance_level),
                    is_core_posttraining = COALESCE(?, is_core_posttraining),
                    include_in_reading_queue = COALESCE(?, include_in_reading_queue),
                    include_in_knowledge_patches = COALESCE(?, include_in_knowledge_patches),
                    include_in_share_pool = COALESCE(?, include_in_share_pool),
                    reviewer_comment = COALESCE(?, reviewer_comment)
                WHERE id = ?
            """, (
                tag_data.get("is_candidate", 0),
                tag_data.get("is_relevant", 0),
                tag_data.get("model_type", "Other"),
                post_training_types_str,
                problem_tags_str,
                keywords_matched_str,
                tag_data.get("confidence", 0.0),
                tag_data.get("reason", ""),
                now,
                tag_data.get("reading_status"),
                tag_data.get("priority"),
                tag_data.get("share_status"),
                tag_data.get("my_rating"),
                tag_data.get("next_action"),
                matched_evidence_str,
                tag_data.get("relevance_level"),
                tag_data.get("is_core_posttraining"),
                tag_data.get("include_in_reading_queue"),
                tag_data.get("include_in_knowledge_patches"),
                tag_data.get("include_in_share_pool"),
                tag_data.get("reviewer_comment"),
                tag_id
            ))
        else:
            self.conn.execute("""
                INSERT INTO paper_tags (
                    paper_id, is_candidate, is_relevant, model_type, post_training_types,
                    problem_tags, keywords_matched, confidence, reason, classified_at,
                    reading_status, priority, share_status, my_rating, next_action, matched_evidence,
                    relevance_level, is_core_posttraining, include_in_reading_queue,
                    include_in_knowledge_patches, include_in_share_pool, reviewer_comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                tag_data.get("is_candidate", 0),
                tag_data.get("is_relevant", 0),
                tag_data.get("model_type", "Other"),
                post_training_types_str,
                problem_tags_str,
                keywords_matched_str,
                tag_data.get("confidence", 0.0),
                tag_data.get("reason", ""),
                now,
                tag_data.get("reading_status", "Unread"),
                tag_data.get("priority", "Medium"),
                tag_data.get("share_status", "Not Started"),
                tag_data.get("my_rating"),
                tag_data.get("next_action"),
                matched_evidence_str,
                tag_data.get("relevance_level", "D_Irrelevant"),
                tag_data.get("is_core_posttraining", 0),
                tag_data.get("include_in_reading_queue", 0),
                tag_data.get("include_in_knowledge_patches", 0),
                tag_data.get("include_in_share_pool", 0),
                tag_data.get("reviewer_comment", "")
            ))
        self.conn.commit()

    def insert_run(self, run_data):
        now = datetime.now().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO runs (source, venue, year, total_count, candidate_count, relevant_count, run_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                run_data["source"],
                run_data["venue"],
                run_data["year"],
                run_data.get("total_count", 0),
                run_data.get("candidate_count", 0),
                run_data.get("relevant_count", 0),
                now
            ))

    def get_classified_papers(self, venue=None, year=None):
        """
        Retrieves all papers joined with their tags.
        """
        query = """
            SELECT p.*, t.is_candidate, t.is_relevant, t.model_type, t.post_training_types,
                   t.problem_tags, t.keywords_matched, t.confidence, t.reason, t.classified_at,
                   t.reading_status, t.priority, t.share_status, t.my_rating, t.next_action,
                   t.matched_evidence, t.relevance_level, t.is_core_posttraining, t.include_in_reading_queue,
                   t.include_in_knowledge_patches, t.include_in_share_pool, t.reviewer_comment
            FROM papers p
            LEFT JOIN paper_tags t ON p.id = t.paper_id
        """
        params = []
        conditions = []
        if venue:
            conditions.append("p.venue = ?")
            params.append(venue)
        if year:
            conditions.append("p.year = ?")
            params.append(year)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            item = dict(r)
            item["authors"] = json.loads(item["authors"]) if item["authors"] else []
            item["post_training_types"] = json.loads(item["post_training_types"]) if item["post_training_types"] else []
            item["problem_tags"] = json.loads(item["problem_tags"]) if item["problem_tags"] else []
            item["keywords_matched"] = json.loads(item["keywords_matched"]) if item["keywords_matched"] else []
            item["matched_evidence"] = json.loads(item["matched_evidence"]) if item["matched_evidence"] else {}
            results.append(item)
        return results

    def update_siyuan_meta(self, paper_id, doc_id, doc_path, sync_time=None, sync_mode=None):
        """
        Updates the SiYuan doc ID and path for a paper.
        """
        with self.conn:
            self.conn.execute(
                "UPDATE papers SET siyuan_doc_id = ?, siyuan_path = ?, siyuan_sync_time = ?, siyuan_sync_mode = ? WHERE id = ?",
                (doc_id, doc_path, sync_time, sync_mode, paper_id)
            )

    def close(self):
        self.conn.close()
