import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from storage.models import Ticket, Message
from config import DATA_FILE

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self):
        self.data = {"tickets": {}, "users": {}}
        self.load()

    def load(self):
        """Load data from file"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    self.data["users"] = raw.get("users", {})

                    # Convert tickets to objects
                    tickets_raw = raw.get("tickets", {})
                    self.data["tickets"] = {
                        tid: Ticket.from_dict(tdata) for tid, tdata in tickets_raw.items()
                    }
                logger.info(f"Loaded {len(self.data['tickets'])} tickets and {len(self.data['users'])} users")
            except Exception as e:
                logger.error(f"Error loading data: {e}", exc_info=True)
                self.data = {"tickets": {}, "users": {}}

    def save(self):
        """Save data to file"""
        try:
            # Convert tickets to dict for JSON
            tickets_dict = {tid: t.to_dict() for tid, t in self.data["tickets"].items()}

            output = {
                "tickets": tickets_dict,
                "users": self.data["users"]
            }

            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            logger.debug("Data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}", exc_info=True)

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID"""
        return self.data["tickets"].get(ticket_id)

    def create_ticket(self, ticket: Ticket):
        """Create new ticket"""
        self.data["tickets"][ticket.id] = ticket
        self.save()

    def update_ticket(self, ticket: Ticket):
        """Update existing ticket"""
        if ticket.id in self.data["tickets"]:
            self.data["tickets"][ticket.id] = ticket
            self.save()

    def delete_ticket(self, ticket_id: str):
        """Delete ticket"""
        if ticket_id in self.data["tickets"]:
            del self.data["tickets"][ticket_id]
            self.save()

    def get_all_tickets(self) -> List[Ticket]:
        """Get all tickets"""
        return list(self.data["tickets"].values())

    def get_tickets_by_status(self, status: str) -> List[Ticket]:
        """Get tickets by status"""
        return [t for t in self.data["tickets"].values() if t.status == status]

    def get_user_data(self, user_id: int) -> dict:
        """Get user data"""
        user_id_str = str(user_id)
        if user_id_str not in self.data["users"]:
            self.data["users"][user_id_str] = {
                "last_review": None,
                "last_suggestion": None,
                "thanked": False
            }
        return self.data["users"][user_id_str]

    def update_user_data(self, user_id: int, updates: dict):
        """Update user data"""
        user_id_str = str(user_id)
        if user_id_str not in self.data["users"]:
            self.data["users"][user_id_str] = {}
        self.data["users"][user_id_str].update(updates)
        self.save()

    def get_stats(self) -> dict:
        """Get statistics"""
        tickets = self.get_all_tickets()
        return {
            "total_users": len(self.data["users"]),
            "total_tickets": len(tickets),
            "active_tickets": len([t for t in tickets if t.status in ["new", "working"]]),
            "closed_tickets": len([t for t in tickets if t.status == "done"])
        }

# Global instance
data_manager = DataManager()
