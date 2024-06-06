# APx_opentrons_resources
A collection of code resources for opentrons liquid-handling systems.

Instructions to upload metadata files that are needed in addition to a python script to the OT-2. This is managed via ssh/scp procotol.

SSH access was set up according to https://support.opentrons.com/s/article/Setting-up-SSH-access-to-your-OT-2. To ssh to our OT-2, open a command line window (windows + r, type cmd and enter) and use the following command:

```
ssh -i .ssh/ot2_ssh_key root@169.254.113.174
```

To transfer a file from this computer to the OT-2, use the following command:

```
scp -i .ssh/ot2_ssh_key "path/to/your/file.csv" root@169.254.113.174:/path/on/OT-2
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

