from opentrons import protocol_api
from opentrons.protocol_api import Well
import pandas as pd
from sys import platform
from typing import Optional

# helper function to distribute with more flexibility
def distribute(volume: int,
               source: Well,
               dest: list[Well],
               delay: int,
               residual_volume: int,
               pipette,
               protocol: protocol_api.ProtocolContext,
               blow_out_height_from_bottom: int,
               blow_out_location: Optional[Well] = None,):

    # iterate over destination sublists and aspirate
    pipette.pick_up_tip()     
    pipette.aspirate(
        volume=len(dest)*volume + residual_volume, 
        location=source,
    )
    # iterate over each destination and dispense 5 ul
    for destination in dest:
        pipette.dispense(
            volume=volume,
            location=destination,
        )
        # short delay
        protocol.delay(seconds=delay)

    if blow_out_location is not None:
        pipette.blow_out(location=blow_out_location.bottom(z=blow_out_height_from_bottom))
    # drop tip
    pipette.drop_tip()
