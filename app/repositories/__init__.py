"""Persistence repositories grouped by business domain.

Repositories own query construction and organization scoping. Web routes and
services should not duplicate tenant filters when an equivalent repository
function exists.
"""
