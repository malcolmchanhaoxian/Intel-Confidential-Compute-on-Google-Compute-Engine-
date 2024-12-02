# Intel-Confidential-Compute-on-Google-Compute-Engine-

## Introduction

This is a project to demonstrate the use of Intel's confidential computing on Google Compute Engine (GCE) combined with remote attestation using Intel Trust Authority.
This project achieves following outcomes:
1. Build a Trust Domain Extension Enabled (TDX) Guest VM on Google Cloud.
2. Perform remote attestation via Intel Trust Authority.
3. Set up a workflow for a remote user to use remote attestation to verify a Confidential VM.

#### A few things to note:

1. The main difference here is that we are setting up a confidential compute virtual machine on cloud rather than on a baremetal so certain services are taken care for by the Cloud Hyperscaler. (https://cc-enabling.trustedservices.intel.com/intel-tdx-enabling-guide/01/introduction#reading-guideline)
   <p align="center"><img src = "https://github.com/user-attachments/assets/b09015b6-ccf6-498c-8ec7-568acda35c3c" width = "700"></p>

3. At the time of this posting, creation of Intel TDX-enabled VM on Google Cloud is only possible by using API or Google Cloud Shell
4. Intel TDX-enabled VM is enabled on Google Compute Engine C3 shape


## VM Creation

To run the confidential VM, we will be using the gcloud shell. The details used are show below.<br>
The full details is contained within the VM Creation text file.
Official Google Documentation here: [link](https://cloud.google.com/confidential-computing/confidential-vm/docs/create-a-confidential-vm-instance)
```sh
gcloud compute instances create tdx-host \
    --confidential-compute-type="TDX" \
    --project=<YOURPROJECT> \
    --zone=asia-southeast1-a \
    --machine-type=c3-standard-4 \
    --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
    --maintenance-policy=TERMINATE \
    --provisioning-model=STANDARD \
    --service-account=732801563947-compute@developer.gserviceaccount.com \
```

A recommended alternative is to replicate your usual VM creation code using the 'Equivalent Code' functionality in Google Cloud console. Then you can add the additional commands for TDX in the gcloudshell. 

## Configuring TDX Client Pre-requisites

1. Verify TDX is enabled. This verifies that the VM is Intel TDX-enabled.
```
ll /dev/tpmrm0
#or
dmesg | grep tdx
```
## Setup Remote Attestation
For our case, we are using Intel Trust Authority for remote attestation. Rather than using the client bindings directly in a sample application, we are using the Intel TDX CLI client which provides a command-line wrapper for the Golang client libraries.
```
#Download and run the installer
curl -sL https://raw.githubusercontent.com/intel/trustauthority-client-for-go/main/release/install-tdx-cli.sh | sudo bash -

#Verify the CLI
trustauthority-cli version

#Configure the URL and API key
cat <<EOF | tee config.json
{
 	"trustauthority_url": "https://portal.trustauthority.intel.com",
 	"trustauthority_api_url": "https://api.trustauthority.intel.com",
    "trustauthority_api_key": "<attestation api key>"
}
EOF
```

#### Running Trust Authority CLI
There are multiple commands you can run using the CLI but we are interested specifically in the ones that generated a valid attestation token (_trustauthority-cli token_)<br>
You can use the help function to see all the optional arguemnets for the token function but the recommendation would be to use the following:
```
trustauthority-cli token -c <config.json file path> --policy-ids <policy ID number> --policy-must-match <boolean> --tdx true
```

1. Config File - Ensure that your Intel Trust Authority URL and API URL are correct. You will have been assigned an API Key as part of your sign up and subscription to the service.
2. Policy ID - Policy IDs are composed of either an appraisal policy or custom indentifiers. These policies are included in the Trust Authority Portal and you can get the Policy ID directly from the portal.
3. Set policy matching to True (Optional). The token generation will still run if policies does not match as it is up to the appraiser/relying party to verifiy if they should access the Trust Domain given the token results. 
4. Set TDX to true to collect TDX evidence

## Trust Workflow 
1. The trust model has three primary actors in the attestation workflow mainly; Attester, Verifier and Relying Party. Each actor establishes trust in a different way.
    - **Attester** — This is the confidential computing workload that needs to prove its authenticity and integrity to relying parties. Trust is established by collecting evidence from the attester; which is then evaluated by the verifier. This produces an **attestation token**
    - **Relying party** — This entity evaluates an attestation token by applying its own evaluation (appraisal) policy to determine if it should trust the attester for authorizing access or releasing a secret
    - **Verifier** — Intel Trust Authority
