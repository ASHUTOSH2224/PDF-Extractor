#!/usr/bin/env python3
"""
Database migration script to add user_id columns to existing projects and documents.

This script should be run once after deploying the security updates.
It will:
1. Add user_id column to projects and documents tables if they don't exist
2. Add user tracking columns (user_id, user_name) to document_page_feedback and annotations tables
3. Create performance indexes for user tracking columns
4. Create a default admin user if no users exist
5. Assign all existing projects and documents to the default admin user
6. Add unique constraint to document_page_feedback to ensure one rating per user/page/extractor
7. Clean up any duplicate ratings before adding the constraint

Usage: python migration.py
"""

import asyncio
import sqlite3
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from .db import get_db, engine_async
from .models import User, Project, Document
from .auth.security import hash_password
from .constants import ADMIN_NAME, ADMIN_EMAIL, ADMIN_PASSWORD

DEFAULT_ADMIN_NAME = ADMIN_NAME or "Admin"
DEFAULT_ADMIN_EMAIL = ADMIN_EMAIL or "admin@example.com"
DEFAULT_ADMIN_PASSWORD = ADMIN_PASSWORD or "admin123"

async def run_migration():
    """Run the database migration"""
    print("Starting database migration...")
    
    # Locate the SQLite DB file, prioritizing the path next to this script
    here = Path(__file__).resolve()
    src_db_path = here.with_name("pdf-extraction.db")  # .../src/pdf-extraction.db
    app_root_db_path = src_db_path.parent.parent / "pdf-extraction.db"  # .../pdf-extraction.db

    candidate_paths = [
        str(src_db_path),                        # preferred (same dir as running app models)
        str(app_root_db_path),                   # app root (container path)
        "/app/src/pdf-extraction.db",          # container explicit
        "/app/pdf-extraction.db",              # container alt
        "backend/src/pdf-extraction.db",       # repo-relative heuristic
        "./pdf-extraction.db",                 # CWD
        "pdf-extraction.db",                   # fallback
    ]

    db_file = next((p for p in candidate_paths if os.path.exists(p)), None)
    if db_file:
        print(f"Found SQLite database: {db_file}")
        await migrate_sqlite(db_file)
    else:
        print("No SQLite database file found at known paths; nothing to migrate.")
        return
    
    print("Migration completed successfully!")

async def migrate_sqlite(db_file: str):
    """Migrate SQLite database"""
    # First, check if columns already exist using raw SQL
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        # Check if user_id column exists in projects table
        cursor.execute("PRAGMA table_info(projects)")
        projects_columns = [col[1] for col in cursor.fetchall()]
        
        # Check if user_id column exists in documents table
        cursor.execute("PRAGMA table_info(documents)")
        documents_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"Projects table columns: {projects_columns}")
        print(f"Documents table columns: {documents_columns}")
        
        # Add user_id column to projects if it doesn't exist
        if 'user_id' not in projects_columns:
            print("Adding user_id column to projects table...")
            cursor.execute("ALTER TABLE projects ADD COLUMN user_id INTEGER")
            print("✓ Added user_id column to projects table")
        else:
            print("user_id column already exists in projects table")

        # Add owner_name column to projects if it doesn't exist
        if 'owner_name' not in projects_columns:
            print("Adding owner_name column to projects table...")
            cursor.execute("ALTER TABLE projects ADD COLUMN owner_name VARCHAR")
            print("✓ Added owner_name column to projects table")
        else:
            print("owner_name column already exists in projects table")

        # Add file_upload_type column to projects if it doesn't exist
        if 'file_upload_type' not in projects_columns:
            print("Adding file_upload_type column to projects table...")
            cursor.execute("ALTER TABLE projects ADD COLUMN file_upload_type VARCHAR")
            print("✓ Added file_upload_type column to projects table")
        else:
            print("file_upload_type column already exists in projects table")

        # Add deleted_at column to projects if it doesn't exist
        if 'deleted_at' not in projects_columns:
            print("Adding deleted_at column to projects table...")
            cursor.execute("ALTER TABLE projects ADD COLUMN deleted_at DATETIME")
            print("✓ Added deleted_at column to projects table")
        else:
            print("deleted_at column already exists in projects table")
        
        # Add user_id column to documents if it doesn't exist
        if 'user_id' not in documents_columns:
            print("Adding user_id column to documents table...")
            cursor.execute("ALTER TABLE documents ADD COLUMN user_id INTEGER")
            print("✓ Added user_id column to documents table")
        else:
            print("user_id column already exists in documents table")

        # Add file_type column to documents if it doesn't exist
        if 'file_type' not in documents_columns:
            print("Adding file_type column to documents table...")
            # default to 'pdf' for existing rows to satisfy NOT NULL
            cursor.execute("ALTER TABLE documents ADD COLUMN file_type VARCHAR NOT NULL DEFAULT 'pdf'")
            print("✓ Added file_type column to documents table")
        else:
            print("file_type column already exists in documents table")

        # Add page_count column to documents if it doesn't exist
        if 'page_count' not in documents_columns:
            print("Adding page_count column to documents table...")
            cursor.execute("ALTER TABLE documents ADD COLUMN page_count INTEGER")
            print("✓ Added page_count column to documents table")
        else:
            print("page_count column already exists in documents table")

        # Add project_uuid column to documents if it doesn't exist
        if 'project_uuid' not in documents_columns:
            print("Adding project_uuid column to documents table...")
            cursor.execute("ALTER TABLE documents ADD COLUMN project_uuid VARCHAR")
            print("✓ Added project_uuid column to documents table")
        else:
            print("project_uuid column already exists in documents table")
        
        # Add owner_name column to documents if it doesn't exist
        if 'owner_name' not in documents_columns:
            print("Adding owner_name column to documents table...")
            cursor.execute("ALTER TABLE documents ADD COLUMN owner_name VARCHAR")
            print("✓ Added owner_name column to documents table")
        else:
            print("owner_name column already exists in documents table")
        
        # Add deleted_at column to documents if it doesn't exist
        if 'deleted_at' not in documents_columns:
            print("Adding deleted_at column to documents table...")
            cursor.execute("ALTER TABLE documents ADD COLUMN deleted_at DATETIME")
            print("✓ Added deleted_at column to documents table")
        else:
            print("deleted_at column already exists in documents table")
        
        # Add deleted_at column to document_extraction_jobs if it doesn't exist
        cursor.execute("PRAGMA table_info(document_extraction_jobs)")
        extraction_jobs_columns = [col[1] for col in cursor.fetchall()]
        if 'deleted_at' not in extraction_jobs_columns:
            print("Adding deleted_at column to document_extraction_jobs table...")
            cursor.execute("ALTER TABLE document_extraction_jobs ADD COLUMN deleted_at DATETIME")
            print("✓ Added deleted_at column to document_extraction_jobs table")
        else:
            print("deleted_at column already exists in document_extraction_jobs table")

        # Add deleted_at column to document_page_content if it doesn't exist
        cursor.execute("PRAGMA table_info(document_page_content)")
        page_content_columns = [col[1] for col in cursor.fetchall()]
        if 'deleted_at' not in page_content_columns:
            print("Adding deleted_at column to document_page_content table...")
            cursor.execute("ALTER TABLE document_page_content ADD COLUMN deleted_at DATETIME")
            print("✓ Added deleted_at column to document_page_content table")
        else:
            print("deleted_at column already exists in document_page_content table")

        # Add deleted_at column to document_page_feedback if it doesn't exist
        cursor.execute("PRAGMA table_info(document_page_feedback)")
        page_feedback_columns = [col[1] for col in cursor.fetchall()]
        if 'deleted_at' not in page_feedback_columns:
            print("Adding deleted_at column to document_page_feedback table...")
            cursor.execute("ALTER TABLE document_page_feedback ADD COLUMN deleted_at DATETIME")
            print("✓ Added deleted_at column to document_page_feedback table")
        else:
            print("deleted_at column already exists in document_page_feedback table")

        # Add user tracking columns to document_page_feedback if they don't exist
        if 'user_id' not in page_feedback_columns:
            print("Adding user_id column to document_page_feedback table...")
            cursor.execute("ALTER TABLE document_page_feedback ADD COLUMN user_id INTEGER REFERENCES users(id)")
            print("✓ Added user_id column to document_page_feedback table")
        else:
            print("user_id column already exists in document_page_feedback table")

        if 'user_name' not in page_feedback_columns:
            print("Adding user_name column to document_page_feedback table...")
            cursor.execute("ALTER TABLE document_page_feedback ADD COLUMN user_name TEXT")
            print("✓ Added user_name column to document_page_feedback table")
        else:
            print("user_name column already exists in document_page_feedback table")

        # Add deleted_at column to annotations if it doesn't exist
        cursor.execute("PRAGMA table_info(annotations)")
        annotations_columns = [col[1] for col in cursor.fetchall()]
        if 'deleted_at' not in annotations_columns:
            print("Adding deleted_at column to annotations table...")
            cursor.execute("ALTER TABLE annotations ADD COLUMN deleted_at DATETIME")
            print("✓ Added deleted_at column to annotations table")
        else:
            print("deleted_at column already exists in annotations table")

        # Add user tracking columns to annotations if they don't exist
        if 'user_id' not in annotations_columns:
            print("Adding user_id column to annotations table...")
            cursor.execute("ALTER TABLE annotations ADD COLUMN user_id INTEGER REFERENCES users(id)")
            print("✓ Added user_id column to annotations table")
        else:
            print("user_id column already exists in annotations table")

        if 'user_name' not in annotations_columns:
            print("Adding user_name column to annotations table...")
            cursor.execute("ALTER TABLE annotations ADD COLUMN user_name TEXT")
            print("✓ Added user_name column to annotations table")
        else:
            print("user_name column already exists in annotations table")
        
        # Add name/approval/role/org columns to users if they don't exist
        cursor.execute("PRAGMA table_info(users)")
        users_columns = [col[1] for col in cursor.fetchall()]
        if 'name' not in users_columns:
            print("Adding name column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN name VARCHAR")
            print("\u2713 Added name column to users table")
        else:
            print("name column already exists in users table")

        if 'is_approved' not in users_columns:
            print("Adding is_approved column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT 0")
            print("\u2713 Added is_approved column to users table")
        else:
            print("is_approved column already exists in users table")

        if 'role' not in users_columns:
            print("Adding role column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'")
            print("\u2713 Added role column to users table")
        else:
            print("role column already exists in users table")

        if 'organization_name' not in users_columns:
            print("Adding organization_name column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN organization_name VARCHAR")
            print("\u2713 Added organization_name column to users table")
        else:
            print("organization_name column already exists in users table")

        if 'organization_id' not in users_columns:
            print("Adding organization_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN organization_id VARCHAR")
            print("\u2713 Added organization_id column to users table")
        else:
            print("organization_id column already exists in users table")

        if 'last_login' not in users_columns:
            print("Adding last_login column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
            print("\u2713 Added last_login column to users table")
        else:
            print("last_login column already exists in users table")

        # Ensure annotations table has new columns
        cursor.execute("PRAGMA table_info(annotations)")
        annotations_columns = [col[1] for col in cursor.fetchall()]
        print(f"Annotations table columns: {annotations_columns}")

        if 'extraction_job_uuid' not in annotations_columns:
            print("Adding extraction_job_uuid column to annotations table...")
            cursor.execute("ALTER TABLE annotations ADD COLUMN extraction_job_uuid VARCHAR")
            print("\u2713 Added extraction_job_uuid column to annotations table")
        else:
            print("extraction_job_uuid column already exists in annotations table")

        if 'page_number' not in annotations_columns:
            print("Adding page_number column to annotations table...")
            cursor.execute("ALTER TABLE annotations ADD COLUMN page_number INTEGER")
            print("\u2713 Added page_number column to annotations table")
        else:
            print("page_number column already exists in annotations table")

        # Create indexes for better query performance
        print("Creating indexes for user tracking columns...")
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON document_page_feedback(user_id)")
            print("✓ Created index on document_page_feedback.user_id")
        except Exception as e:
            print(f"Note: Index creation skipped (may already exist): {e}")
        
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_user_id ON annotations(user_id)")
            print("✓ Created index on annotations.user_id")
        except Exception as e:
            print(f"Note: Index creation skipped (may already exist): {e}")

        # Add unique constraint for document_page_feedback ratings
        print("Adding unique constraint for document_page_feedback ratings...")
        
        # Check for existing duplicates first
        cursor.execute("""
            SELECT COUNT(*) as total_duplicates
            FROM (
                SELECT document_uuid, page_number, extraction_job_uuid, user_id, COUNT(*) as cnt
                FROM document_page_feedback
                WHERE deleted_at IS NULL AND user_id IS NOT NULL
                GROUP BY document_uuid, page_number, extraction_job_uuid, user_id
                HAVING COUNT(*) > 1
            ) duplicates
        """)
        duplicate_count = cursor.fetchone()[0]
        
        if duplicate_count > 0:
            print(f"⚠️  Found {duplicate_count} duplicate rating groups")
            print("🧹 Cleaning up duplicates (keeping most recent rating per user/page/extractor)...")
            
            # Delete duplicate ratings, keeping only the most recent one
            cursor.execute("""
                DELETE FROM document_page_feedback
                WHERE uuid IN (
                    SELECT uuid FROM (
                        SELECT uuid,
                               ROW_NUMBER() OVER (
                                   PARTITION BY document_uuid, page_number, extraction_job_uuid, user_id 
                                   ORDER BY created_at DESC
                               ) as rn
                        FROM document_page_feedback
                        WHERE deleted_at IS NULL AND user_id IS NOT NULL
                    ) ranked
                    WHERE rn > 1
                )
            """)
            print(f"✅ Cleaned up {cursor.rowcount} duplicate rating records")
        else:
            print("✅ No duplicate ratings found")
        
        # Check if constraint already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM sqlite_master 
            WHERE type='index' 
            AND name='uq_user_page_extractor_rating'
        """)
        constraint_exists = cursor.fetchone()[0] > 0
        
        if constraint_exists:
            print("ℹ️  Rating unique constraint already exists")
        else:
            # Create the unique constraint (as a partial unique index for SQLite)
            cursor.execute("""
                CREATE UNIQUE INDEX uq_user_page_extractor_rating
                ON document_page_feedback(document_uuid, page_number, extraction_job_uuid, user_id)
                WHERE deleted_at IS NULL AND user_id IS NOT NULL
            """)
            print("✅ Created unique constraint for document_page_feedback ratings")
        
        # Verify the constraint
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' 
            AND name='uq_user_page_extractor_rating'
        """)
        if cursor.fetchone():
            print("✅ Rating unique constraint verified")
        else:
            print("❌ Rating unique constraint verification failed")

        conn.commit()
        
    except Exception as e:
        print(f"Error during column addition: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
    
    # Now use SQLAlchemy to handle user creation and data assignment.
    # Ensure the async engine/session point to the EXACT same DB file we just migrated.
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from . import db as dbmod
    db_url = f"sqlite+aiosqlite:///{Path(db_file).resolve()}"
    dbmod.engine_async = create_async_engine(db_url, echo=False)
    dbmod.AsyncSessionLocal = async_sessionmaker(bind=dbmod.engine_async, expire_on_commit=False, class_=AsyncSession)

    async with dbmod.engine_async.begin() as conn:
        # Create tables to ensure they're up to date
        from .models import Base
        await conn.run_sync(Base.metadata.create_all)
    
    # Use the async session for the rest
    async for db_session in dbmod.get_db():
        try:
            # Ensure an admin user exists matching ADMIN_EMAIL
            print(f"Using ADMIN_EMAIL from env: {DEFAULT_ADMIN_EMAIL}")
            result = await db_session.execute(select(User).where(User.email == DEFAULT_ADMIN_EMAIL))
            admin_user = result.scalar_one_or_none()
            if admin_user is None:
                # If no users exist at all, create admin; otherwise also create admin
                print("Admin user not found, creating from .env...")
                admin_user = User(
                    name=DEFAULT_ADMIN_NAME,
                    email=DEFAULT_ADMIN_EMAIL,
                    hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
                    is_active=True,
                    is_approved=True,
                    role='admin'
                )
                db_session.add(admin_user)
                await db_session.commit()
                await db_session.refresh(admin_user)
                print(f"✓ Created admin user with email: {DEFAULT_ADMIN_EMAIL}")
            else:
                # Update flags to guarantee access; optionally sync password
                updated = False
                if not getattr(admin_user, 'is_active', True):
                    admin_user.is_active = True
                    updated = True
                if not getattr(admin_user, 'is_approved', False):
                    admin_user.is_approved = True
                    updated = True
                if getattr(admin_user, 'role', 'user') != 'admin':
                    admin_user.role = 'admin'
                    updated = True
                # Always reset password to env for deterministic access
                admin_user.hashed_password = hash_password(DEFAULT_ADMIN_PASSWORD)
                updated = True
                if updated:
                    print("✓ Ensured admin user flags and password are up to date")
                    await db_session.commit()

            admin_user_id = admin_user.id
            print(f"Using admin user (id: {admin_user_id}) for orphaned data")
            
            # Update projects without user_id
            result = await db_session.execute(
                select(Project).where(Project.user_id.is_(None))
            )
            orphaned_projects = result.scalars().all()
            
            if orphaned_projects:
                print(f"Found {len(orphaned_projects)} projects without user_id, assigning to user {admin_user_id}")
                for project in orphaned_projects:
                    project.user_id = admin_user_id
                await db_session.commit()
                print("✓ Updated orphaned projects")
            else:
                print("No orphaned projects found")
            
            # Update documents without user_id
            result = await db_session.execute(
                select(Document).where(Document.user_id.is_(None))
            )
            orphaned_documents = result.scalars().all()
            
            if orphaned_documents:
                print(f"Found {len(orphaned_documents)} documents without user_id, assigning to user {admin_user_id}")
                for document in orphaned_documents:
                    document.user_id = admin_user_id
                await db_session.commit()
                print("✓ Updated orphaned documents")
            else:
                print("No orphaned documents found")
            
            break  # Exit the async generator
            
        except Exception as e:
            print(f"Error during data migration: {e}")
            await db_session.rollback()
            raise

async def rollback_rating_constraint():
    """Rollback: Remove the rating unique constraint"""
    print("🔄 Rolling back: Removing rating unique constraint")
    
    # Find the database file
    here = Path(__file__).resolve()
    src_db_path = here.with_name("pdf-extraction.db")
    app_root_db_path = src_db_path.parent.parent / "pdf-extraction.db"
    
    candidate_paths = [
        str(src_db_path),
        str(app_root_db_path),
        "/app/src/pdf-extraction.db",
        "/app/pdf-extraction.db",
        "backend/src/pdf-extraction.db",
        "./pdf-extraction.db",
        "pdf-extraction.db",
    ]
    
    db_file = next((p for p in candidate_paths if os.path.exists(p)), None)
    if not db_file:
        print("❌ No database file found")
        return False
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DROP INDEX IF EXISTS uq_user_page_extractor_rating")
        conn.commit()
        print("✅ Rating unique constraint rollback completed")
        return True
    except Exception as e:
        print(f"❌ Error during rollback: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration script')
    parser.add_argument('--rollback-rating-constraint', action='store_true', 
                       help='Rollback the rating unique constraint')
    args = parser.parse_args()
    
    if args.rollback_rating_constraint:
        asyncio.run(rollback_rating_constraint())
    else:
        asyncio.run(run_migration())
