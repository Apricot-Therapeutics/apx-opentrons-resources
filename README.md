# APx_opentrons_resources
A collection of code resources for opentrons liquid-handling systems.

Instructions to upload metadata files that are needed in addition to a python script to the OT-2. This is managed via ssh/scp procotol.

SSH access was set up according to https://support.opentrons.com/s/article/Setting-up-SSH-access-to-your-OT-2. To ssh to our OT-2, open a command line window (windows + r, type cmd and enter) and use the following command:

```
ssh -i .ssh/ot2_ssh_key root@169.254.113.174
```

To transfer a file from this computer to the OT-2, use the following command (You do not have to run the previous command beforehand):

```
scp -i .ssh/ot2_ssh_key "path/to/your/file.csv" root@169.254.113.174:/path/on/OT-2
```

For example, for the OVP protocols, the metadata files are saved at /data/user_storage/apricot_data/:

```
scp -i .ssh/ot2_ssh_key "C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\drug_plate_metadata_v1.3.csv" root@169.254.113.174:/data/user_storage/apricot_data/
```

I recently ran this again and scp transfer failed with the following error:

```
sh: /usr/libexec/sftp-server: not found
scp: Connection closed
```
I haven't completely followed up on it, but it seems to be an issue with the ssh version, see this github issue: https://github.com/Opentrons/opentrons/issues/12910

The workaround for now is to use the -O argument in the scp call:

```
scp -i .ssh/ot2_ssh_key -O "C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\drug_plate_metadata_v1.3.csv" root@169.254.113.174:/data/user_storage/apricot_data/
```

If you are trying to give some csv files to your protocol, you have to be a bit sneaky after uploading them to the OT-2. Stupidly, when importing a python script in the software, it will try to load the csv files defined in the script locally - but later on again on the raspberry PI running the OT-2. Current strategy to circumvent is to use the following in the python protocol when reading in the csv files:

```python
from sys import platform

if platform == "win32":
        # load the layout from local path
        plate_layout = pd.read_csv("/local/path/to/csv")

elif platform == "linux":
        # load layout from location on OT-2 computer
        plate_layout = pd.read_csv("/OT-2/path/to/csv")
```

Not elegant, but it works.

