from opentrons import protocol_api
from opentrons.protocol_api import Well
import pandas as pd
from sys import platform
import numpy as np

# helper function to distribute with more flexibility
def distribute(volume: int,
               source: Well,
               dest: list[Well],
               delay: int,
               residual_volume: int,
               pipette,
               protocol: protocol_api.ProtocolContext):

    # iterate over destination sublists and aspirate
    pipette.pick_up_tip()     
    pipette.aspirate(
        volume=len(dest)*volume,
        location=source,
    )
    # iterate over each destination and dispense 5 ul
    for destination in dest:
        pipette.dispense(
            volume=volume,
            location=destination,
        )
        # short delay
        protocol.delay(seconds=0.5)
    # drop tip
    pipette.drop_tip()

# metadata
metadata = {
    "protocolName": "OVP Drug Transfer to 384-well Cell Plate (single patient)",
    "description": """This protocol is used to transfer drugs from a
     pre-prepared 96-well drug plate to a 384 well plate containing patient
     cells (in 45 ul of media) in a randomized layout.""",
    "author": "Adrian Tschan"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.16"}

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 1)
    #drug_plate = protocol.load_labware("greinermasterblock_96_wellplate_2000ul", 5)
    #cell_plate = protocol.load_labware("greiner_bio_one_384_well_plate_100ul_reduced_well_size", 6)

    # for local testing
    drug_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    cell_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 3)

    # optional: set liquids
    sample = protocol.define_liquid(name="sample", display_color="#1c03fc",
                                    description="sample to which to add drugs")
    drugs = protocol.define_liquid(name="drugs", display_color="#fcba03",
                                 description="drugs to be transferred")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate and final 384-well plate
        drug_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\Apricot\OVP\metadata\drug_plate_metadata_v1.2.csv")
        cell_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\Apricot\OVP\metadata\plate_metadata_v1.1.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate and final 384-well plate
        drug_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/drug_plate_metadata_v1.2.csv")
        cell_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/plate_metadata_v1.1.csv")

    # for now, only 1 patient
    cell_plate_metadata = cell_plate_metadata.loc[
        cell_plate_metadata["sample"] != "patient_2"]

    # load drugs into 96-well plate
    for i, well in drug_plate_metadata.iterrows():
        well = drug_plate[well.row + str(well.col)]
        well.load_liquid(liquid=drugs, volume=1000)

    for i, well in cell_plate_metadata.iterrows():
        well = cell_plate[well.row + str(well.col)]
        well.load_liquid(liquid=sample, volume=45)

    # initialize pipette
    left_pipette = protocol.load_instrument("p20_multi_gen2", "left",
                                            tip_racks=[tips])
    right_pipette = protocol.load_instrument("p20_single_gen2", "right",
                                            tip_racks=[tips])

    # set well clearance of pipettes
    left_pipette.well_bottom_clearance.aspirate = 0.5
    left_pipette.well_bottom_clearance.dispense = 2
    right_pipette.well_bottom_clearance.aspirate = 0.5
    right_pipette.well_bottom_clearance.dispense = 2

    # get unique names of drugs and whether they are combinations
    drug_list = cell_plate_metadata[["condition", "combination"]]
    drug_list = drug_list.drop_duplicates()

    single_drugs = drug_list.loc[drug_list.combination == False]
    combination_drugs = drug_list.loc[drug_list.combination == True]

    # distribute single drugs
    for i, drug in single_drugs.iterrows():
        # get source well
        source = drug_plate_metadata.loc[
            drug_plate_metadata.condition == drug.condition]
        source = source.loc[source["sample"] == "1000x"]

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
        # chunk destinations in order to change tip after each aspiration
        chunked_destinations = np.array_split(destinations, len(destinations)/3)
        print(f"Distributing {drug.condition} from well {source_well} "
              f"to wells {dest_wells} on 384-well cell plate")
        # iterate over destination sublists and aspirate
        for destination_list in chunked_destinations:
            distribute(
                volume=5,
                source=drug_plate[source_well],
                dest=destination_list,
                delay=0.5,
                pipette=right_pipette,
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
        source_1 = source_1.loc[source_1["sample"] == "2000x"]

        source_2 = drug_plate_metadata.loc[
            drug_plate_metadata.condition == drug_2]
        source_2 = source_2.loc[source_2["sample"] == "2000x"]

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
        # chunk destinations in order to change tip after each aspiration
        chunked_destinations = np.array_split(destinations, len(destinations)/3)
        print(f"Distributing {drug.condition} from well {source_well_1}"
                    f" and {source_well_2} to wells {dest_wells} on "
                    f"384-well cell plate")
        
        # iterate over destination sublists and aspirate
        for destination_list in chunked_destinations:
            distribute(
                volume=2.5,
                source=drug_plate[source_well],
                dest=destination_list,
                delay=0.5,
                pipette=right_pipette,
                residual_volume=5,
                protocol=protocol,
            )

    






