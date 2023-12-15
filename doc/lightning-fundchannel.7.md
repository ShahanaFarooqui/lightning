lightning-fundchannel -- Command for establishing a lightning channel
=====================================================================

SYNOPSIS
--------

**fundchannel** *id* *amount* [*feerate*] [*announce*] [*minconf*] [*push_msat*] [*close_to*] [*request_amt*] [*compact_lease*] [*utxos*] [*mindepth*] [*reserve*]

DESCRIPTION
-----------

The **fundchannel** RPC command opens a payment channel with a peer by committing a 
funding transaction to the blockchain as defined in BOLT #2.

If not already connected, **fundchannel** will automatically attempt to connect if 
Core Lightning knows a way to contact the node (either from normal gossip, or from 
a previous **connect** call).

This auto-connection can fail if Core Lightning does not know how to contact the 
target node; see lightning-connect(7).

Once the transaction is confirmed, normal channel operations may begin. Readiness 
is indicated by **listpeers** reporting a *state* of `CHANNELD_NORMAL` for the channel.

This example shows how to use lightning-cli to open new channel with peer 03f...fc1 from one whole utxo bcc1...39c:0
(you can use **listfunds** command to get txid and vout):

	lightning-cli -k fundchannel id=03f...fc1 amount=all feerate=normal utxos='["bcc1...39c:0"]'

RETURN VALUE
------------

On success, an object is returned, containing:

- **tx** (hex): The raw transaction which funded the channel
- **txid** (txid): The txid of the transaction which funded the channel
- **outnum** (u32): The 0-based output index showing which output funded the channel
- **channel_id** (hex): The channel_id of the resulting channel (always 64 characters)
- **close_to** (hex, optional): The raw scriptPubkey which mutual close will go to; only present if *close_to* parameter was specified and peer supports `option_upfront_shutdown_script`
- **mindepth** (u32, optional): Number of confirmations before we consider the channel active.

ERROR
------

The following error codes may occur:

- -1: Catchall nonspecific error.
- 300: The maximum allowed funding amount is exceeded.
- 301: There are not enough funds in the internal wallet (including fees) to create the transaction.
- 302: The output amount is too small, and would be considered dust.
- 303: Broadcasting of the funding transaction failed, the internal call to bitcoin-cli returned with an error.
- 313: The `min-emergency-msat` reserve not be preserved (and we have or are opening anchor channels).

Failure may also occur if **lightningd** and the peer cannot agree on channel parameters (funding limits, channel reserves, fees, etc.).

SEE ALSO
--------

lightning-connect(7), lightning-listfunds(), lightning-listpeers(7),lightning-feerates(7), lightning-multifundchannel(7)

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:8f80263a6a56f45168d90a73ed72735ae53dbc7db64729aa38117959d8dfb54c)
