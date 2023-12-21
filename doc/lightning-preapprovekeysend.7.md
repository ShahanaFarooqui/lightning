lightning-preapprovekeysend -- Ask the HSM to preapprove a keysend payment (low-level)
==================================================================

SYNOPSIS
--------

**preapprovekeysend** *destination* *payment\_hash* *amount\_msat*

DESCRIPTION
-----------

The **preapprovekeysend** RPC command submits the *destination*, *payment\_hash*,
and *amount\_msat* parameters to the HSM to check that they are approved as a
keysend payment.

Generally the **preapprovekeysend** request does not need to be made
explicitly, it is automatically generated as part of a **keysend** request.

By default, the HSM will approve all **preapprovekeysend** requests.

If a remote signer is being used it might decline an **preapprovekeysend**
request because it would exceed velocity controls, is not covered by
allowlist controls, was declined manually, or other reasons.

If a remote signer declines a **preapprovekeysend** request a subsequent
attempt to pay the keysend anyway will fail; the signer will refuse to sign
the commitment.

RETURN VALUE
------------

[comment]: # (GENERATE-FROM-SCHEMA-START)
On success, an empty object is returned.

[comment]: # (GENERATE-FROM-SCHEMA-END)

AUTHOR
------

Ken Sedgwick <<ken@bonsai.com>> is mainly responsible.

SEE ALSO
--------

lightning-keysend(7)

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:41d0ca6a956520453538c8ad5c5afce681540f4ce26017570cdc2356c3aab599)
