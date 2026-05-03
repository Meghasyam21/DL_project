import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONTACTS_FILE = Path(__file__).parent / "contacts.json"


def load_contacts():
    if CONTACTS_FILE.exists():
        with open(CONTACTS_FILE, "r") as f:
            return json.load(f)
    return {"emails": [], "phones": []}


def save_contacts(contacts):
    with open(CONTACTS_FILE, "w") as f:
        json.dump(contacts, f, indent=2)
    logger.info("Contacts saved: %s", contacts)


def register_email(email: str):
    contacts = load_contacts()
    if email not in contacts["emails"]:
        contacts["emails"].append(email)
        save_contacts(contacts)
        return True
    return False


def register_phone(phone: str):
    contacts = load_contacts()
    if phone not in contacts["phones"]:
        contacts["phones"].append(phone)
        save_contacts(contacts)
        return True
    return False


def unregister_email(email: str):
    contacts = load_contacts()
    if email in contacts["emails"]:
        contacts["emails"].remove(email)
        save_contacts(contacts)
        return True
    return False


def unregister_phone(phone: str):
    contacts = load_contacts()
    if phone in contacts["phones"]:
        contacts["phones"].remove(phone)
        save_contacts(contacts)
        return True
    return False


def get_all_contacts():
    return load_contacts()
