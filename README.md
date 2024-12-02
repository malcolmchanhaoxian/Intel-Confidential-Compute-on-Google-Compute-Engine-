# Intel-Confidential-Compute-on-Google-Cloud

![image](https://github.com/user-attachments/assets/64920924-9cec-4e1e-bb00-cc557efcb919)


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
There are multiple commands you can run using the CLI but we are interested specifically in the ones that generated a valid attestation token (_trustauthority-cli token_). You can use the help function to see all the optional arguemnets for the token function but the recommendation would be to use the below. For references, see [link](https://docs.trustauthority.intel.com/main/articles/integrate-go-tdx-cli.html)
```
trustauthority-cli token -c <config.json file path> --policy-ids <policy ID number> --policy-must-match <boolean> --tdx true
```

1. Config File - Ensure that your Intel Trust Authority URL and API URL are correct. You will have been assigned an API Key as part of your sign up and subscription to the service.
2. Policy ID - Policy IDs are composed of either an appraisal policy or custom indentifiers. These policies are included in the Trust Authority Portal and you can get the Policy ID directly from the portal.
3. Set policy matching to True (Optional). The token generation will still run if policies does not match as it is up to the appraiser/relying party to verifiy if they should access the Trust Domain given the token results. 
4. Set TDX to true to collect TDX evidence

## Trust Model 
1. The trust model has three primary actors in the attestation workflow mainly; Attester, Verifier and Relying Party. Each actor establishes trust in a different way.
    - **Attester** — This is the confidential computing workload that needs to prove its authenticity and integrity to relying parties. Trust is established by collecting evidence from the attester; which is then evaluated by the verifier. This produces an **attestation token**
    - **Relying party** — This entity evaluates an attestation token by applying its own evaluation (appraisal) policy to determine if it should trust the attester for authorizing access or releasing a secret
    - **Verifier** — Intel Trust Authority

<p align="center"><img src = "https://github.com/user-attachments/assets/dd05f380-4965-48be-8e57-46a435657d6a" width = "500"></p>

#### Workflow
1. The attesting workload obtains a quote from the Trust Domain by using the Intel Trust Authority CLI, which is also used to request an attestation token from Intel Trust Authority.
2. Intel Trust Authority evaluates the quote and returns an attestation token.
3. The workload forwards the attestation token to a REST API request by the Relying Party
4. The Relying Party evaluates the token and applies its trust policy and compares values in the attestation token.
5. If the release policy evaluation is successful (that is, all compared values match), trust is established.
6. Detailed model which includes Key Broker services to encrypt/decrypt workload within Trust Domain; see [HERE] (https://docs.trustauthority.intel.com/main/articles/tutorial-tdx-workload.html)

#### REST API Request
Run a python script to establish REST API on the Attester VM. Successful API request will execute the Trust Authority CLI. See repository file for full python command.
```
def get_token():
    """
    Endpoint to execute the trustauthority-cli command with optional policy-id and match-policy flags.
    """
    # Parse JSON input from client
    data = request.json
    policy_id = data.get("policy-id", "").strip()
    match_policy = data.get("match-policy", False)  # Default to False

    # Base command
    command = ['trustauthority-cli', 'token', '-c', 'config.json', '--tdx', 'true']
    # Match Policies
    command.extend(['--policy-ids', policy_id, '--policy-must-match')
```

Relying Party can perform a _curl_ request to obtain an attestation token
```
curl -X POST <IP-ADDRESS>/get_token \
     -H "Content-Type: application/json" \
     -d '{"policy-id": "POLICY-ID-NUMBER", "match-policy": true}' | jq -r '.data' > token.jwt
```

#### Validate Token
Once relying part obtains token, Relying Party can leverage many methods by the verfier to very and decode the token to get the token details. For simplicity, we will use just a jwt decoding functionality
```
pip install jwt
jwt -show token.jwt
```
<br>
A sample of the decoded token is included in this repository. There are many details provided but to establish trust on the attester - below are the minimum requirements

- Verify the nonce (if present)
- Verify that the token signature matches Intel Trust Authority certificates
- Verify that the token has not expired
- Check the lists of matched and unmatched policies
- Check that the TEE debug flag is false

```
    "attester_tcb_date": "2024-03-13T00:00:00Z",
    "attester_tcb_status": "OutOfDate",
    "attester_type": "TDX",
    "policy_ids_matched": [
        {
            "hash": "akNva0lUd0JlT1g0SVE1Y0pwckZtWEI1Y2c4MWJlVmJ1SWZjWEhjb0JRWW4yRktPR3VFTGc1WUt2VDNkRDhpbg==",
            "id": "749dd9b1-234f-41f5-a6ca-42c4312dd4f1",
            "version": "v1"
        }
    "policy_ids_unmatched": null,
    "tdx_is_debuggable": false,
```

#### TCB Status
As seen from the decoded token, the attestation is showing that the TCB status is out of date. The Intel platform TCB (Trusted Compute Base) comprises the components that are critical to meeting Intel's platform security objectives. Table below describes possible results of TCB status. More details [HERE] (https://docs.trustauthority.intel.com/main/articles/concept-platform-tcb.html)

| TCB Status Value                | Description                                                                                             |
|---------------------------------|---------------------------------------------------------------------------------------------------------|
| **UpToDate**                    | The attesting platform is patched with the latest firmware and software and no known security advisories apply. |
| **SWHardeningNeeded**           | The platform firmware and software are at the latest security patching level but there are vulnerabilities that can only be mitigated by software changes to the enclave or TD. |
| **ConfigurationNeeded**         | The platform firmware and software are at the latest security patching level but there are platform hardware configurations required to mitigate vulnerabilities. |
| **ConfigurationAndSWHardeningNeeded** | Both of the above.                                                                                     |
| **OutOfDate**                   | The attesting platform software and/or firmware is not patched in accordance with the latest TCB Recovery (TCB-R). |
| **OutOfDateConfigurationNeeded** | The attesting platform is not patched in accordance with the latest TCB-R. Hardware configuration is needed. |

## Useful Links
- https://docs.trustauthority.intel.com/main/articles/tutorial-tdx.html
- https://docs.trustauthority.intel.com/main/articles/integrate-relying-party.html#relying-party-sample-workflow
- https://portal.trustauthority.intel.com/certs
- https://docs.trustauthority.intel.com/main/articles/concept-attestation-tokens.html?tabs=sgx%2Csgx-token
- https://docs.trustauthority.intel.com/main/articles/concept-platform-tcb.html
- https://docs.trustauthority.intel.com/main/articles/utility-policy-builder.html?tabs=sgx-json%2Ctdx-json%2Ctcb-json%2Csgx-custom-json%2Ctdx-custom-json%2Cv2-sgx-json%2Cv2-tdx-json%2Cv2-sevsp-json%2Cnvgpu-json%2Ctpm-json%2Ctdx-nvgpu-json%2Ctdx-tpm-json%2Csevnsnp-nvgpu-json%2Csevnsnp-tpm-json%2Ctdx-nvgpu-tpm-json#token-customization-policies
