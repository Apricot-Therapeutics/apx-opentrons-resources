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

# helper function to consolidate with more flexibility
def consolidate(volume: int,
               source: list[Well],
               dest: Well,
               pipette,
               protocol: protocol_api.ProtocolContext,
               aspirate_delay: float = 0,
               dispense_delay: float = 0,
               touch_tip_radius: Optional[float] = None,
               touch_tip_v_offset: Optional[float] = None,
               touch_tip: bool = False,
               aspirate_rate: float = 1.0,
               dispense_rate: float = 1.0,
               reuse_tips=False,
               ignore_tips=False):
    
    # based on the volume, calculate how often can be pipetted
    n_pipetting_steps = np.floor((300)/volume) # TO-DO: max volume of pipette
    
    # chunk up the destinations
    chunked_dest = np.array_split(source, np.ceil(len(source)/n_pipetting_steps))

    for i, sub_list in enumerate(chunked_dest):
        if ignore_tips == False:
            if reuse_tips == False:
                pipette.pick_up_tip()
            if (reuse_tips == True) & (i == 0):
                pipette.pick_up_tip() 

        # iterate over each destination and dispense 5 ul
        for source in sub_list:
            pipette.aspirate(
                volume=volume,
                location=source,
                rate=aspirate_rate
            )
            # short delay
            protocol.delay(seconds=dispense_delay)

        # iterate over destination sublists and aspirate
        pipette.dispense(
            volume=len(sub_list)*volume, 
            location=dest,
            rate=dispense_rate
        )

        if touch_tip:
                pipette.touch_tip(radius=touch_tip_radius,
                                  v_offset=touch_tip_v_offset) 

        # short delay
        protocol.delay(seconds=aspirate_delay)

        # drop tip
        if ignore_tips == False:
            if (reuse_tips == False) or (i == (len(chunked_dest) -1)):
                pipette.drop_tip()

# metadata
metadata = {
    "protocolName": "OVP Post PFA PBS Wash",
    "description": """This protocol is used to wash a 384-well plate
    with PBS after PFA fixation.""",
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
    variable_name="exclude_experimental_drugs",
    display_name="Exclude experimental drugs",
    description="Turn on if the experimental drug set should be excluded.",
    default=False,
    )

    parameters.add_bool(
    variable_name="process_full_plate",
    display_name="Process two patient samples",
    description="Turn on if there are two patient samples on the plate (full plate).",
    default=False,
    )

    parameters.add_int(
    variable_name="n_wash",
    display_name="Number of wash cycles",
    description="How many wash cycles with PBS should be performed?",
    minimum=1,
    maximum=100,
    default=4,
    )

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("integra150ml_1_reservoir_150000ul", 5)
    trash = protocol.load_labware("integra150ml_1_reservoir_150000ul", 9)
    cell_plate = protocol.load_labware("greiner_bio_one_384_well_plate_100ul_reduced_well_size", 6)

    # optional: set liquids
    sample = protocol.define_liquid(name="sample", display_color="#1c03fc",
                                    description="wells that will contain sample")
    PBS = protocol.define_liquid(name="PBS", display_color="#1c03fc",
                                 description="PBS for washing")
    waste_PBS = protocol.define_liquid(name="waste PBS", display_color="#1c03fc",
                                    description="waste PBS collection")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\plate_metadata_v1.2.csv")

    elif platform == "linux":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/plate_metadata_v1.2.csv")

    # process one or two patient samples
    if protocol.params.process_full_plate == False:
        cell_plate_metadata = cell_plate_metadata.loc[
            cell_plate_metadata["sample"] != "patient_2"]
    
    # include or exclude experimental drugs
    if protocol.params.exclude_experimental_drugs:
        cell_plate_metadata = cell_plate_metadata.loc[cell_plate_metadata.drug_panel == "standard"]

    for i, well in cell_plate_metadata.iterrows():
        well = cell_plate[well.row + str(well.col)]
        well.load_liquid(liquid=sample, volume=90)

    # load media into reservoir
    reservoir['A1'].load_liquid(liquid=PBS, volume=50000)
    trash['A1'].load_liquid(liquid=waste_PBS, volume=100000)

    # initialize pipette
    pipette = protocol.load_instrument("p300_multi_gen2", "left",
                                       tip_racks=[tips])

    # set well clearance of pipettes
    pipette.well_bottom_clearance.aspirate = 3
    pipette.well_bottom_clearance.dispense = 3.5

    dest_wells = [[row + str(col) for col in cell_plate_metadata.col.unique()] for row in ["A", "B"]]
    dest_wells = list(itertools.chain.from_iterable(dest_wells))
    destinations = [cell_plate[well] for well in dest_wells]

    source_well = "A1"

    pipette.pick_up_tip()

    consolidate(
        volume=50,
        source=destinations,
        dest=trash[source_well],
        aspirate_delay=0,
        dispense_delay=0,
        aspirate_rate=0.2,
        pipette=pipette,
        protocol=protocol,
        touch_tip=False,
        ignore_tips=True,
        )
    
    for i in range(0, protocol.params.n_wash):
        distribute(
            volume=60,
            source=reservoir[source_well],
            dest=destinations,
            aspirate_delay=0,
            dispense_delay=0,
            dispense_rate=0.2,
            residual_volume=20,
            pipette=pipette,
            protocol=protocol,
            residual_dispense_location=reservoir[source_well],
            residual_dispense_height_from_bottom=3.5,
            touch_tip=False,
            ignore_tips=True,
            )
        
        if i == (protocol.params.n_wash - 1):
            consolidate_volume = 50
        else:
            consolidate_volume = 60
        
        consolidate(
            volume=consolidate_volume,
            source=destinations,
            dest=trash[source_well],
            aspirate_delay=0,
            dispense_delay=0,
            aspirate_rate=0.2,
            pipette=pipette,
            protocol=protocol,
            touch_tip=False,
            ignore_tips=True,
            )
        
    pipette.drop_tip()
    


