from __future__ import annotations

# Canonical public contact handoff semantics shared by the endpoint and runtime gates.
# Keep these values free of framework/database imports so certification scripts can
# consume them without bootstrapping the application.
PUBLIC_CONTACT_SUCCESS_STATE = "recibido"
PUBLIC_CONTACT_SUCCESS_LOCATION = f"/contacto?estado={PUBLIC_CONTACT_SUCCESS_STATE}"
PUBLIC_CONTACT_LEAD_STATUS = "Nuevo"
PUBLIC_CONTACT_LEAD_SOURCE = "Contacto público same-origin"
