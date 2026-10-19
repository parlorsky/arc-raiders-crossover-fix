# Components

The patch manifests describe changes to the Wine runtime supplied in a local
CrossOver installation. The Wine-derived compatibility patch layer follows
LGPL-2.1-or-later; the license text is in COPYING.LIB. Wine and CodeWeavers
retain attribution to their respective runtime code.

- Wine: https://www.winehq.org/
- CrossOver and runtime source releases: https://www.codeweavers.com/crossover
- REA, used during analysis: https://github.com/morluto/rea

This repository contains patch recipes and original scripts, with no complete
CrossOver runtime, game executable, anti-cheat DLL, Steam bottle, account data,
or diagnostic memory dump. The scripts operate on the user's own local files.
The private launcher applies a local compatibility tweak to copies of the
anti-cheat runtime inside that private installation; no anti-cheat binary is
distributed.

ARC Raiders, Steam, CrossOver, and their names belong to their respective
owners. This is a community experiment with no claim of vendor endorsement.
