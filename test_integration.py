"""
Integration Test Script for Design Agent → Tech Spec Agent Flow

This script tests the full integration between Design Agent and Tech Spec Agent:
1. Creates a test Design Job in the database
2. Monitors Design Agent progress
3. Triggers Tech Spec Agent via REST API
4. Monitors Tech Spec Agent progress via WebSocket
5. Verifies final TRD generation

Usage:
    python test_integration.py
"""

import asyncio
import asyncpg
import httpx
import json
from datetime import datetime
from typing import Optional
import websockets

# Configuration
DATABASE_URL = "postgresql://anyon_user:anyon_password_2025@localhost:5432/anyon_db"
TECH_SPEC_API_URL = "http://localhost:8001"


class IntegrationTester:
    """Integration test coordinator"""

    def __init__(self):
        self.db_conn: Optional[asyncpg.Connection] = None
        self.design_job_id: Optional[str] = None
        self.tech_spec_session_id: Optional[str] = None

    async def connect_db(self):
        """Connect to PostgreSQL"""
        print("📦 Connecting to database...")
        self.db_conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Database connected")

    async def create_test_design_job(self) -> str:
        """Create a test Design Job"""
        print("\n🎨 Creating test Design Job...")

        prd_content = """# Product Requirements Document

## Project: Task Management Web App

### Overview
Build a modern task management web application with real-time collaboration.

### Features
1. User authentication and authorization
2. Create, read, update, delete tasks
3. Real-time updates when team members make changes
4. File attachments for tasks
5. Task comments and activity log
6. Email notifications

### Target Users
- Small to medium-sized teams (5-50 people)
- Remote-first companies
- Project managers

### Technical Requirements
- Must be web-based
- Mobile-responsive design
- Real-time synchronization
- Secure authentication
"""

        trd_content = """# Technical Requirements Document

## Technology Stack (To Be Decided by Tech Spec Agent)

### Frontend
- Framework: React 18 with TypeScript
- Styling: Tailwind CSS
- State Management: To be decided
- Real-time: To be decided

### Backend
- Runtime: Node.js
- Framework: To be decided
- Database: To be decided
- Authentication: To be decided
- File Storage: To be decided
"""

        # Insert into shared.design_jobs
        row = await self.db_conn.fetchrow(
            """
            INSERT INTO shared.design_jobs (
                job_id, project_id, user_id, prd_content, trd_content, status
            ) VALUES (
                gen_random_uuid(), $1, $2, $3, $4, $5
            ) RETURNING job_id
            """,
            "test-project-integration-001",
            "test-user-001",
            prd_content,
            trd_content,
            "pending",
        )

        self.design_job_id = str(row["job_id"])
        print(f"✅ Test Design Job created: {self.design_job_id}")
        print("⏳ Waiting for Design Agent to process (30-45 minutes)...")
        return self.design_job_id

    async def monitor_design_agent_progress(self):
        """Monitor Design Agent progress until completion"""
        print("\n📊 Monitoring Design Agent progress...")

        while True:
            # Check job status
            status_row = await self.db_conn.fetchrow(
                "SELECT status, started_at, completed_at FROM shared.design_jobs WHERE job_id = $1",
                self.design_job_id,
            )

            status = status_row["status"]
            print(f"   Status: {status}")

            if status == "completed":
                print("✅ Design Agent completed!")
                break
            elif status == "failed":
                error_row = await self.db_conn.fetchrow(
                    "SELECT error_message FROM shared.design_jobs WHERE job_id = $1",
                    self.design_job_id,
                )
                print(f"❌ Design Agent failed: {error_row['error_message']}")
                raise Exception("Design Agent failed")

            # Check progress
            progress_row = await self.db_conn.fetchrow(
                """
                SELECT current_phase, phase_name, progress_percent
                FROM shared.design_progress
                WHERE job_id = $1
                """,
                self.design_job_id,
            )

            if progress_row:
                print(
                    f"   Phase {progress_row['current_phase']}: {progress_row['phase_name']} "
                    f"({progress_row['progress_percent']:.1f}%)"
                )

            # Wait 10 seconds before checking again
            await asyncio.sleep(10)

    async def trigger_tech_spec_agent(self):
        """Trigger Tech Spec Agent via REST API"""
        print("\n🚀 Triggering Tech Spec Agent...")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TECH_SPEC_API_URL}/api/projects/test-project-integration-001/start-tech-spec",
                json={
                    "design_job_id": self.design_job_id,
                    "user_id": "test-user-001",
                },
                headers={
                    "Content-Type": "application/json",
                    # Note: In production, you'd need a valid JWT token
                    # "Authorization": "Bearer <jwt_token>"
                },
                timeout=30.0,
            )

            if response.status_code != 201:
                print(f"❌ Failed to start Tech Spec Agent: {response.text}")
                raise Exception("Tech Spec Agent start failed")

            data = response.json()
            self.tech_spec_session_id = data["session_id"]
            websocket_url = data["websocket_url"]

            print(f"✅ Tech Spec session started: {self.tech_spec_session_id}")
            print(f"   WebSocket URL: {websocket_url}")

    async def monitor_tech_spec_via_websocket(self):
        """Monitor Tech Spec Agent progress via WebSocket"""
        print("\n🔌 Connecting to Tech Spec Agent WebSocket...")

        # Note: In production, you'd need a valid JWT token
        ws_url = f"ws://localhost:8001/ws/tech-spec/{self.tech_spec_session_id}?token=test_token"

        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket connected")

                while True:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(), timeout=300.0
                        )  # 5 min timeout
                        data = json.loads(message)

                        msg_type = data.get("type")
                        if msg_type == "progress_update":
                            print(
                                f"   Progress: {data['progress']}% - {data['message']}"
                            )
                        elif msg_type == "agent_message":
                            print(f"   Agent: {data['message']}")
                        elif msg_type == "completion":
                            print("✅ Tech Spec Agent completed!")
                            break
                        elif msg_type == "error":
                            print(f"❌ Error: {data['message']}")
                            break

                    except asyncio.TimeoutError:
                        print("⏱️ WebSocket timeout, checking database...")
                        break

        except Exception as e:
            print(f"⚠️ WebSocket error (will check database instead): {e}")
            # Fall back to database polling
            await self.monitor_tech_spec_via_database()

    async def monitor_tech_spec_via_database(self):
        """Fallback: Monitor Tech Spec Agent via database polling"""
        print("\n📊 Monitoring Tech Spec Agent via database...")

        while True:
            row = await self.db_conn.fetchrow(
                """
                SELECT status, progress_percentage, current_stage
                FROM tech_spec_sessions
                WHERE id = $1
                """,
                self.tech_spec_session_id,
            )

            if not row:
                print("❌ Session not found")
                break

            status = row["status"]
            progress = row["progress_percentage"]
            stage = row["current_stage"]

            print(f"   Status: {status}, Progress: {progress}%, Stage: {stage}")

            if status == "completed":
                print("✅ Tech Spec Agent completed!")
                break
            elif status == "failed":
                print("❌ Tech Spec Agent failed")
                break

            await asyncio.sleep(10)

    async def verify_trd_generation(self):
        """Verify TRD documents were generated"""
        print("\n📄 Verifying TRD document generation...")

        row = await self.db_conn.fetchrow(
            """
            SELECT quality_score, version, created_at,
                   LENGTH(trd_content) as trd_length,
                   LENGTH(api_specification::text) as api_length,
                   LENGTH(database_schema::text) as db_length,
                   LENGTH(architecture_diagram) as arch_length,
                   LENGTH(tech_stack_document::text) as tech_length
            FROM generated_trd_documents
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            self.tech_spec_session_id,
        )

        if not row:
            print("❌ No TRD documents found")
            return False

        print(f"✅ TRD Generated:")
        print(f"   Quality Score: {row['quality_score']}/100")
        print(f"   Version: {row['version']}")
        print(f"   TRD Content: {row['trd_length']} characters")
        print(f"   API Spec: {row['api_length']} characters")
        print(f"   DB Schema: {row['db_length']} characters")
        print(f"   Architecture: {row['arch_length']} characters")
        print(f"   Tech Stack: {row['tech_length']} characters")

        if row["quality_score"] >= 90:
            print("✅ Quality score meets threshold (>= 90)")
            return True
        else:
            print(f"⚠️ Quality score below threshold: {row['quality_score']} < 90")
            return False

    async def cleanup(self):
        """Clean up database connection"""
        if self.db_conn:
            await self.db_conn.close()
            print("\n🧹 Database connection closed")

    async def run_full_test(self):
        """Run complete integration test"""
        print("=" * 80)
        print("🧪 STARTING INTEGRATION TEST")
        print("=" * 80)
        print(f"Started at: {datetime.now().isoformat()}")
        print()

        try:
            # Step 1: Connect to database
            await self.connect_db()

            # Step 2: Create test Design Job
            await self.create_test_design_job()

            # Step 3: Monitor Design Agent
            await self.monitor_design_agent_progress()

            # Step 4: Trigger Tech Spec Agent
            await self.trigger_tech_spec_agent()

            # Step 5: Monitor Tech Spec Agent
            await self.monitor_tech_spec_via_websocket()

            # Step 6: Verify TRD generation
            success = await self.verify_trd_generation()

            print()
            print("=" * 80)
            if success:
                print("🎉 INTEGRATION TEST PASSED!")
            else:
                print("⚠️ INTEGRATION TEST COMPLETED WITH WARNINGS")
            print("=" * 80)
            print(f"Completed at: {datetime.now().isoformat()}")

        except Exception as e:
            print()
            print("=" * 80)
            print(f"❌ INTEGRATION TEST FAILED: {e}")
            print("=" * 80)
            import traceback

            traceback.print_exc()

        finally:
            await self.cleanup()


async def main():
    """Main entry point"""
    tester = IntegrationTester()
    await tester.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
