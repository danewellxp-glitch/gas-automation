from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import pytz

from app.database import get_db
from app.models.auth_models import User, Contact
from app.api.auth import get_current_user
from app.services.whatsapp_service import waha_service
from app.schemas.chat_schemas import ContactOut

router = APIRouter(prefix="/api/contacts", tags=["contacts"])
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

@router.get("", response_model=List[ContactOut])
def list_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List valid synced contacts"""
    contacts = db.query(Contact).filter(Contact.is_valid_whatsapp == True).all()
    return contacts

@router.post("/sync")
async def sync_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync contacts from WAHA and filter broken numbers"""
    waha_contacts = await waha_service.get_contacts()
    
    if not waha_contacts:
        raise HTTPException(status_code=400, detail="Could not fetch contacts from WAHA")
    
    added_count = 0
    updated_count = 0
    
    for w_contact in waha_contacts:
        # Some contacts from WAHA might be groups or status broadcasts.
        # Skip if 'id' looks like a group (g.us) or status (status@broadcast)
        contact_id = w_contact.get("id", "")
        if not contact_id or "@c.us" not in contact_id:
            continue
            
        # Clean phone number (remove @c.us)
        phone = contact_id.split("@")[0]
        
        # Additional formatting could happen here
        
        # Check if number is actually valid via check_number_status endpoint in WAHA
        validation = await waha_service.check_number_status(phone)
        is_valid = validation.get("numberExists", True) # Default to true if the check fails 
        
        existing_contact = db.query(Contact).filter(Contact.phone_number == phone).first()
        
        name = w_contact.get("name") or w_contact.get("pushname") or phone
        
        if existing_contact:
            existing_contact.name = name
            existing_contact.is_valid_whatsapp = is_valid
            existing_contact.last_synced_at = datetime.now(BRAZIL_TZ)
            updated_count += 1
        else:
            new_contact = Contact(
                phone_number=phone,
                name=name,
                is_valid_whatsapp=is_valid,
            )
            db.add(new_contact)
            added_count += 1
            
    db.commit()
    
    return {
        "message": f"Sync completed. Added {added_count}, updated {updated_count}.",
        "added": added_count,
        "updated": updated_count
    }
