from opentrons import protocol_api
from opentrons.protocol_api import Well
import pandas as pd
from sys import platform
from typing import Optional
import numpy as np

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
               dispense_rate: float = 1.0,):
    
    # based on the volume, calculate how often can be pipetted
    n_pipetting_steps = np.floor((20 - residual_volume)/volume) # TO-DO: max volume of pipette
    
    # chunk up the destinations
    chunked_dest = np.array_split(dest, np.ceil(len(dest)/n_pipetting_steps))

    for sub_list in chunked_dest:
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
        pipette.drop_tip()

# metadata
metadata = {
    "protocolName": "OVP Drug Transfer to 384-well Cell Plate",
    "description": """This protocol is used to transfer drugs from a
     pre-prepared 96-well drug plate to a 384 well plate containing patient
     cells (in 45 ul of media) in a randomized layout.""",
    "author": "Adrian Tschan"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.18"}

def add_parameters(parameters: protocol_api.Parameters):

    parameters.add_str(
    variable_name="pipette_position",
    display_name="p20 1-channel position",
    description="Which mount is the 1-Channel 20 µL pipette mounted on?",
    choices=[
        {"display_name": "left", "value": "left"},
        {"display_name": "right", "value": "right"},
    ],
    default="right"
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

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 1)
    drug_plate = protocol.load_labware("greinermasterblock_96_wellplate_2000ul", 5)
    cell_plate = protocol.load_labware("greiner_bio_one_384_well_plate_100ul_reduced_well_size", 6)

    # for local testing
    #drug_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    #cell_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 3)

    # optional: set liquids
    sample = protocol.define_liquid(name="sample", display_color="#1c03fc",
                                    description="sample to which to add drugs")
    drugs = protocol.define_liquid(name="drugs", display_color="#fcba03",
                                 description="drugs to be transferred")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate and final 384-well plate
        drug_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\drug_plate_metadata_v2.0.csv")
        cell_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\plate_metadata_v2.0.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate and final 384-well plate
        drug_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/OVP/drug_plate_metadata_v2.0.csv")
        cell_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/OVP/plate_metadata_v2.0.csv")

    # process one or two patient samples
    if protocol.params.process_full_plate == False:
        cell_plate_metadata = cell_plate_metadata.loc[
            cell_plate_metadata["experimental_unit"] != "patient_2_with_OVCAR3"]
    
    # include or exclude experimental drugs
    if protocol.params.exclude_experimental_drugs:
        cell_plate_metadata = cell_plate_metadata.loc[cell_plate_metadata.drug_panel == "standard"]

    # load drugs into 96-well plate
    for i, well in drug_plate_metadata.iterrows():
        well = drug_plate[well.row + str(well.col)]
        well.load_liquid(liquid=drugs, volume=1000)

    for i, well in cell_plate_metadata.iterrows():
        well = cell_plate[well.row + str(well.col)]
        well.load_liquid(liquid=sample, volume=45)

    # initialize pipette
    pipette = protocol.load_instrument("p20_single_gen2", "right",
                                            tip_racks=[tips])

    # set well clearance of pipettes
    pipette.well_bottom_clearance.aspirate = 1.0
    pipette.well_bottom_clearance.dispense = 2.5

    # get unique names of drugs and whether they are combinations
    drug_list = cell_plate_metadata[["condition", "combination"]]
    drug_list = drug_list.drop_duplicates()

    single_drugs = drug_list.loc[drug_list.combination == False]
    combination_drugs = drug_list.loc[drug_list.combination == True]

    # distribute single drugs
    for i, drug in single_drugs.iterrows():
        print(f"drug is {drug}")
        # get source well
        source = drug_plate_metadata.loc[
            drug_plate_metadata.condition == drug.condition]
        source = source.loc[source["sample"].isin(["1000x", "1000x_ab_drugs"])]

        # assemble name of source well (opentrons take A1 instead of A01)
        source_well = source.row.values[0] + str(source.col.values[0])
        print(f"source well: {source_well}")

        # collect destination wells
        dest_wells = cell_plate_metadata.loc[
            cell_plate_metadata.condition == drug.condition]
        # put together names for destination wells
        dest_wells = [well.row + str(well.col) for i, well
                      in dest_wells.iterrows()]
        
        destinations = [cell_plate[well] for well in dest_wells]
        print(f"Distributing {drug.condition} from well {source_well} "
              f"to wells {dest_wells} on 384-well cell plate")

        distribute(
            volume=5,
            source=drug_plate[source_well],
            dest=destinations,
            dispense_delay=0.5,
            pipette=pipette,
            residual_volume=5,
            protocol=protocol,
        )


    # distribute combination drugs
    for i, drug in combination_drugs.iterrows():
        # get source wells
        drug_1 = drug.condition.split(" + ")[0]
        drug_2 = drug.condition.split(" + ")[1]

        source_1 = drug_plate_metadata.loc[
            drug_plate_metadata.condition == drug_1]
        source_1 = source_1.loc[source_1["sample"].isin(["2000x", "2000x_ab_drugs"])]

        source_2 = drug_plate_metadata.loc[
            drug_plate_metadata.condition == drug_2]
        source_2 = source_2.loc[source_2["sample"].isin(["2000x", "2000x_ab_drugs"])]

        # assemble name of source well (opentrons take A1 instead of A01)
        source_well_1 = source_1.row.values[0] + str(
            source_1.col.values[0])
        source_well_2 = source_2.row.values[0] + str(
            source_2.col.values[0])

        # collect destination wells
        dest_wells = cell_plate_metadata.loc[
            cell_plate_metadata.condition == drug.condition]
        # put together names for destination wells
        dest_wells = [well.row + str(well.col) for i, well
                      in dest_wells.iterrows()]

        destinations = [cell_plate[well] for well in dest_wells]
        
        # iterate over destination sublists and aspirate
        distribute(
            volume=2.5,
            source=drug_plate[source_well_1],
            dest=destinations,
            dispense_delay=0.5,
            pipette=pipette,
            residual_volume=5,
            protocol=protocol,
        )

        distribute(
            volume=2.5,
            source=drug_plate[source_well_2],
            dest=destinations,
            dispense_delay=0.5,
            pipette=pipette,
            residual_volume=5,
            protocol=protocol,
        )

    






