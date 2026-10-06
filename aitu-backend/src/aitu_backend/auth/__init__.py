"""Users, login and rights (implementation 02, plan section 9).

:mod:`.context` holds the user of the request, :mod:`.passwords` the Argon2 hashes,
:mod:`.sessions` the login cookie, :mod:`.throttle` the slow-down after wrong passwords,
:mod:`.rights` the table of who can read and write what (section 9.3), and :mod:`.dependencies` the
one check every route runs before anything else.
"""
