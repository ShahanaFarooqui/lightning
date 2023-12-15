lightning-emergencyrecover -- Command for recovering channels from the emergency.recovery file in the lightning directory
=========================================================================================================================

SYNOPSIS
--------

**emergencyrecover**

DESCRIPTION
-----------

The **emergencyrecover** RPC command fetches data from the emergency.recover file and tries to reconnect to the peer and force him to close the channel. The data in this file has enough information to reconnect and sweep the funds.

This recovery method is not spontaneous and it depends on the peer, so it should be used as a last resort to recover the funds stored in a channel in case of severe data loss.

RETURN VALUE
------------

On success, an object is returned, containing:

- **stubs** (array of strings)
  - Channel IDs of channels successfully inserted.

AUTHOR
------

Aditya <<aditya.sharma20111@gmail.com>> is mainly responsible.

SEE ALSO
--------

lightning-getsharedsecret(7)

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:678c253c9bbd957d0d7f458d4697a66cad4cd7dc4c64b5f650e0e6a1c32d4c9f)
