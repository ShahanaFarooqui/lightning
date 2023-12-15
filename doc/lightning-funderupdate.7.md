lightning-funderupdate -- Command for adjusting node funding v2 channels
========================================================================

SYNOPSIS
--------

**funderupdate** [*policy*] [*policy_mod*] [*leases_only*] [*min_their_funding_msat*] [*max_their_funding_msat*] [*per_channel_min_msat*] [*per_channel_max_msat*] [*reserve_tank_msat*] [*fuzz_percent*] [*fund_probability*] [*lease_fee_base_msat*] [*lease_fee_basis*] [*funding_weight*] [*channel_fee_max_base_msat*] [*channel_fee_max_proportional_thousandths*] [*compact_lease*]

DESCRIPTION
-----------

NOTE: Must have --experimental-dual-fund enabled for these settings to take effect.

For channel open requests using dual funding.

There are three policy options, detailed below:

* `match` -- Contribute *policy_mod* percent of their requested funds.
   Valid *policy_mod* values are 0 to 200. If this is a channel lease
   request, we match based on their requested funds. If it is not a
   channel lease request (and *lease_only* is false), then we match
   their funding amount. Note: any lease match less than 100 will
   likely fail, as clients will not accept a lease less than their request.
* `available` -- Contribute *policy_mod* percent of our available
   node wallet funds. Valid *policy_mod* values are 0 to 100.
* `fixed` -- Contributes a fixed  *policy_mod* sats to v2 channel open requests.

Note: to maximize channel leases, best policy setting is (match, 100).

Setting any of the 5 options from *lease_fee_base_msat*, *lease_fee_basis*, *funding_weight*, *channel_fee_max_base_msat* and, *channel_fee_max_proportional_thousandths* will activate channel leases for this node, and advertise these values via the lightning gossip network. If any one is set, the other values will be the default.

RETURN VALUE
------------

[comment]: # (GENERATE-FROM-SCHEMA-START)
On success, an object is returned, containing:

- **summary** (string): Summary of the current funding policy e.g. (match 100)
- **policy** (string): Policy funder plugin will use to decide how much captial to commit to a v2 open channel request (one of "match", "available", "fixed")
- **policy_mod** (u32): The *policy_mod* is the number or 'modification' to apply to the policy.
- **leases_only** (boolean): Only contribute funds to `option_will_fund` lease requests.
- **min_their_funding_msat** (msat): The minimum funding sats that we require from peer to activate our funding policy.
- **max_their_funding_msat** (msat): The maximum funding sats that we'll allow from peer to activate our funding policy.
- **per_channel_min_msat** (msat): The minimum amount that we will fund a channel open with.
- **per_channel_max_msat** (msat): The maximum amount that we will fund a channel open with.
- **reserve_tank_msat** (msat): Amount of sats to leave available in the node wallet.
- **fuzz_percent** (u32): Percentage to fuzz our funding amount by.
- **fund_probability** (u32): Percent of opens to consider funding. 100 means we'll consider funding every requested open channel request.
- **lease_fee_base_msat** (msat, optional): Flat fee to charge for a channel lease.
- **lease_fee_basis** (u32, optional): Proportional fee to charge for a channel lease, calculated as 1/10,000th of requested funds.
- **funding_weight** (u32, optional): Transaction weight the channel opener will pay us for a leased funding transaction.
- **channel_fee_max_base_msat** (msat, optional): Maximum channel_fee_base_msat we'll charge for routing funds leased on this channel.
- **channel_fee_max_proportional_thousandths** (u32, optional): Maximum channel_fee_proportional_millitionths we'll charge for routing funds leased on this channel, in thousandths.
- **compact_lease** (hex, optional): Compact description of the channel lease parameters.

[comment]: # (GENERATE-FROM-SCHEMA-END)

ERRORS
------

The following error code may occur:

- -32602: If the given parameters are invalid.

AUTHOR
------

@niftynei <<niftynei@gmail.com>> is mainly responsible.

SEE ALSO
--------

lightning-fundchannel(7), lightning-listfunds(7)

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:d1b668fb8b489377151559c908098626bf11550509008b7383f641696582f0ba)
