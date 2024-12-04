from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import Dict, List, Any
import logging

class MongoDBManager:
    def __init__(self):
        self.uri = "mongodb+srv://kelvin-1013:everysecond1013@cluster0.z54oc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.client = None
        self.db = None
        
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client.shillingbot
            self.setup_collections()
            logging.info("Connected to MongoDB successfully")
            return True
        except Exception as e:
            logging.error(f"MongoDB connection error: {str(e)}")
            return False
            
    def setup_collections(self):
        """Setup required collections with indexes"""
        # Bot accounts collection
        self.db.bot_accounts.create_index("phone_number", unique=True)
        
        # Groups collection
        self.db.groups.create_index("group_name", unique=True)
        
        # Messages collection
        self.db.messages.create_index([("bot_id", 1), ("group_id", 1), ("timestamp", -1)])
        
        # Analytics collection
        self.db.analytics.create_index([("date", -1), ("bot_id", 1)])
        
        # Bot activities collection
        self.db.bot_activities.create_index([
            ("bot_id", 1),
            ("activity_type", 1),
            ("timestamp", -1)
        ])
        
        # Error logs collection
        self.db.error_logs.create_index([
            ("bot_id", 1),
            ("error_type", 1),
            ("timestamp", -1)
        ])
        
    def save_bot_account(self, account_data: Dict) -> str:
        """Save bot account information"""
        try:
            # Use update_one with upsert instead of insert_one
            result = self.db.bot_accounts.update_one(
                {"phone_number": account_data["phone"]},  # Query to find existing account
                {
                    "$set": {
                        "phone_number": account_data["phone"],
                        "api_id": account_data["api_id"],
                        "api_hash": account_data["api_hash"],
                        "last_active": datetime.now(timezone.utc),
                        "status": "active"
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc),
                        "daily_message_count": 0
                    }
                },
                upsert=True  # Create new document if not exists
            )
            
            # Get the document ID (either existing or newly inserted)
            if result.upserted_id:
                return str(result.upserted_id)
            else:
                # Find and return the existing document's ID
                doc = self.db.bot_accounts.find_one({"phone_number": account_data["phone"]})
                return str(doc["_id"]) if doc else None
            
        except Exception as e:
            logging.error(f"Error saving bot account: {str(e)}")
            return None
            
    def save_group(self, group_data: Dict) -> str:
        """Save group information"""
        try:
            result = self.db.groups.insert_one({
                "group_name": group_data["name"],
                "member_count": group_data.get("member_count", 0),
                "last_message_time": datetime.now(timezone.utc),
                "performance_score": group_data.get("performance_score", 0),
                "status": "active",
                "created_at": datetime.now(timezone.utc)
            })
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f"Error saving group: {str(e)}")
            return None
            
    def log_message(self, message_data: Dict):
        """Log message sending activity"""
        try:
            self.db.messages.insert_one({
                "bot_id": message_data["bot_id"],
                "group_id": message_data["group_id"],
                "message_text": message_data["text"],
                "status": message_data["status"],
                "timestamp": datetime.now(timezone.utc),
                "media_attached": message_data.get("media_attached", False)
            })
        except Exception as e:
            logging.error(f"Error logging message: {str(e)}")
            
    def update_analytics(self, analytics_data: Dict):
        """Update analytics data"""
        try:
            date = datetime.now(timezone.utc).date()
            self.db.analytics.update_one(
                {"date": date, "bot_id": analytics_data["bot_id"]},
                {
                    "$inc": {
                        "messages_sent": 1,
                        "successful_sends": 1 if analytics_data["status"] == "success" else 0,
                        "failed_sends": 1 if analytics_data["status"] == "failed" else 0
                    },
                    "$set": {
                        "last_updated": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
        except Exception as e:
            logging.error(f"Error updating analytics: {str(e)}")
            
    def get_bot_stats(self, bot_id: str) -> Dict:
        """Get bot statistics"""
        try:
            stats = self.db.analytics.find_one(
                {"bot_id": bot_id, "date": datetime.now(timezone.utc).date()}
            )
            return stats or {}
        except Exception as e:
            logging.error(f"Error getting bot stats: {str(e)}")
            return {}
            
    def get_group_performance(self, days: int = 7) -> List[Dict]:
        """Get group performance metrics"""
        try:
            pipeline = [
                {
                    "$match": {
                        "timestamp": {
                            "$gte": datetime.now(timezone.utc) - timedelta(days=days)
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$group_id",
                        "message_count": {"$sum": 1},
                        "success_rate": {
                            "$avg": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                        }
                    }
                }
            ]
            return list(self.db.messages.aggregate(pipeline))
        except Exception as e:
            logging.error(f"Error getting group performance: {str(e)}")
            return []

    def log_bot_activity(self, activity_data: Dict):
        """Log bot activities"""
        try:
            self.db.bot_activities.insert_one({
                "bot_id": activity_data["bot_id"],
                "activity_type": activity_data["activity_type"],
                "status": activity_data.get("status", "unknown"),
                "timestamp": activity_data["timestamp"],
                "details": {
                    "recipient": activity_data.get("recipient"),
                    "group_name": activity_data.get("group_name"),
                    "error": activity_data.get("error")
                }
            })
        except Exception as e:
            logging.error(f"Error logging bot activity: {str(e)}")

    def get_bot_activity_stats(self, bot_id: str, days: int = 7) -> Dict:
        """Get bot activity statistics"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            pipeline = [
                {
                    "$match": {
                        "bot_id": bot_id,
                        "timestamp": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$activity_type",
                        "total": {"$sum": 1},
                        "success_count": {
                            "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                        },
                        "fail_count": {
                            "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                        }
                    }
                }
            ]
            return list(self.db.bot_activities.aggregate(pipeline))
        except Exception as e:
            logging.error(f"Error getting bot activity stats: {str(e)}")
            return []

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close() 