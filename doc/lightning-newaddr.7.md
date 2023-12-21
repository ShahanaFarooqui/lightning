lightning-newaddr -- Command for generating a new address to be used by Core Lightning
======================================================================================

SYNOPSIS
--------

**newaddr** [*addresstype*]

DESCRIPTION
-----------

The **newaddr** RPC command generates a new address which can
subsequently be used to fund channels managed by the Core Lightning node.

The funding transaction needs to be confirmed before funds can be used.

To send an on-chain payment from the Core Lightning node wallet, use `withdraw`. 

RETURN VALUE
------------

[comment]: # (GENERATE-FROM-SCHEMA-START)
On success, an object is returned, containing:

- **p2tr** (string, optional): The taproot address *(added v23.08)*
- **bech32** (string, optional): The bech32 (native segwit) address
- **p2sh-segwit** (string, optional): The p2sh-wrapped address **deprecated, removal in v23.11**

[comment]: # (GENERATE-FROM-SCHEMA-END)

ERRORS
------

If an unrecognized address type is requested an error message will be
returned.

AUTHOR
------

Felix <<fixone@gmail.com>> is mainly responsible.

SEE ALSO
--------

lightning-listfunds(7), lightning-fundchannel(7), lightning-withdraw(7), lightning-listtransactions(7)

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:f93771e450afe0fc20b2ff9763ba7654d4caf17c35cf45186f2cb9146a67503f)
