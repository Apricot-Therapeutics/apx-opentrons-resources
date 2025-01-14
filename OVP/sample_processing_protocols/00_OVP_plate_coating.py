from opentrons import protocol_api
from opentrons.protocol_api import Well
import pandas as pd
from sys import platform
from typing import Optional
import numpy as np
import itertools

# helper function to distribute with more flexibility
def distribute(volume: int,
               source: Well,
               dest: list[Well],
               pipette,
               protocol: protocol_api.ProtocolContext,
               aspirate_delay: float = 0,
               dispense_delay: float = 0,
               residual_volume: int = 0,
               residual_dispense_height_from_bottom: Optional[int] = None,
               touch_tip_radius: Optional[float] = None,
               touch_tip_v_offset: Optional[float] = None,
               touch_tip: bool = False,
               residual_dispense_location: Optional[Well] = None,
               n_mix: Optional[int] = None,
               aspirate_rate: float = 1.0,
               dispense_rate: float = 1.0,
               reuse_tips=False,
               ignore_tips=False):
    
    # based on the volume, calculate how often can be pipetted
    n_pipetting_steps = np.floor((300 - residual_volume)/volume) # TO-DO: max volume of pipette
    
    # chunk up the destinations
    chunked_dest = np.array_split(dest, np.ceil(len(dest)/n_pipetting_steps))

    for i, sub_list in enumerate(chunked_dest):
        if ignore_tips == False:
            if reuse_tips == False:
                pipette.pick_up_tip()
            if (reuse_tips == True) & (i == 0):
                pipette.pick_up_tip()

        # mix if required
        if n_mix is not None:
            pipette.mix(
                repetitions=n_mix,
                volume=len(sub_list)*volume + residual_volume, 
                location=source,
                rate=aspirate_rate
                )     
        # iterate over destination sublists and aspirate
        pipette.aspirate(
            volume=len(sub_list)*volume + residual_volume, 
            location=source,
            rate=aspirate_rate
        )

        # short delay
        protocol.delay(seconds=aspirate_delay)
        # iterate over each destination and dispense 5 ul
        for destination in sub_list:
            pipette.dispense(
                volume=volume,
                location=destination,
                rate=dispense_rate
            )
            # short delay
            protocol.delay(seconds=dispense_delay)

            if touch_tip:
                pipette.touch_tip(radius=touch_tip_radius,
                                  v_offset=touch_tip_v_offset)

        if residual_dispense_location is not None:
            pipette.dispense(location=residual_dispense_location.bottom(z=residual_dispense_height_from_bottom))
        # drop tip
        if ignore_tips == False:
            if (reuse_tips == False) or (i == (len(chunked_dest) -1)):
                pipette.drop_tip()

# metadata
metadata = {
    "protocolName": "OVP Polylysine/Fibronectin Plate Coating",
    "description": """This protocol is used to coat a 384-well plate
    with Polylysine and Fibronectin before adding patient samples.""",
    "author": "Adrian Tschan"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.18"}

def add_parameters(parameters: protocol_api.Parameters):

    parameters.add_str(
    variable_name="pipette_position",
    display_name="p300 8-channel position",
    description="Which mount is the 8-Channel 300 µL pipette mounted on?",
    choices=[
        {"display_name": "left", "value": "left"},
        {"display_name": "right", "value": "right"},
    ],
    default="left"
    )

    parameters.add_bool(
    variable_name="process_full_plate",
    display_name="Process two patient samples",
    description="Turn on if there are two patient samples on the plate (full plate).",
    default=False,
    )

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    protocol.pause(msg='IMPORTANT: Have the first and last row of tips been removed from column 1-3 of the p300 tip box? If no, remove them before resuming the protocol.')

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    cell_plate = protocol.load_labware("greiner_bio_one_384_well_plate_100ul_reduced_well_size", 6)

    # for local testing
    #drug_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)

    # optional: set liquids
    sample = protocol.define_liquid(name="sample", display_color="#1c03fc",
                                    description="wells that will contain sample")
    coating_solution = protocol.define_liquid(name="polylysine+fibronectin", display_color="#1c03fc",
                                           description="coating solution")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\plate_metadata_v2.0.csv")

    elif platform == "linux":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/OVP/plate_metadata_v2.0.csv")

    # process one or two patient samples
    if protocol.params.process_full_plate == False:
        cell_plate_metadata = cell_plate_metadata.loc[
            cell_plate_metadata["experimental_unit"] != "patient_2_with_OVCAR3"]


    for i, well in cell_plate_metadata.iterrows():
        well = cell_plate[well.row + str(well.col)]
        well.load_liquid(liquid=sample, volume=40)

    # load media into reservoir
    reservoir['A1'].load_liquid(liquid=coating_solution, volume=4500)

    # initialize pipette
    pipette = protocol.load_instrument("p300_multi_gen2", "left",
                                       tip_racks=[tips])

    # set well clearance of pipettes
    pipette.well_bottom_clearance.aspirate = 1.0
    pipette.well_bottom_clearance.dispense = 1.0

    dest_wells = [[row + str(col) for col in cell_plate_metadata.col.unique()] for row in ["A", "B"]]
    dest_wells = list(itertools.chain.from_iterable(dest_wells))
    destinations = [cell_plate[well] for well in dest_wells]

    source_well = "A1"

    pipette.pick_up_tip()

    distribute(
        volume=30,
        source=reservoir[source_well],
        dest=destinations,
        aspirate_delay=1.0,
        dispense_delay=1.0,
        n_mix=1,
        residual_volume=20,
        pipette=pipette,
        protocol=protocol,
        residual_dispense_location=reservoir[source_well],
        residual_dispense_height_from_bottom=1,
        touch_tip=True,
        touch_tip_radius=0.4,
        touch_tip_v_offset=-5,
        ignore_tips=True,
)
    

    pipette.drop_tip()
