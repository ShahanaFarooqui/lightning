lightning-sendonionmessage -- low-level command to send an onion message
================================================================

SYNOPSIS
--------

**sendonionmessage** *first\_id* *blinding* *hops*

DESCRIPTION
-----------

**(WARNING: experimental-onion-messages only)**

The **sendonionmessage** RPC command can be used to send a message via
the lightning network.  These are currently used by *offers* to request
and receive invoices.

RETURN VALUE
------------

[comment]: # (GENERATE-FROM-SCHEMA-START)
On success, an empty object is returned.

[comment]: # (GENERATE-FROM-SCHEMA-END)

AUTHOR
------

Rusty Russell <<rusty@rustcorp.com.au>> is mainly responsible.

SEE ALSO
--------

lightning-fetchinvoice(7), lightning-offer(7).

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[bolt04]: https://github.com/lightning/bolts/blob/master/04-onion-routing.md

[comment]: # ( SHA256STAMP:636acc798ed7ae1cd307ada4dbde424c1ed8aa514600bec9adeacd5778f4d036)
