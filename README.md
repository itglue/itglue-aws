# IT Glue Import Script

This script creates a CloudFormation stack in AWS which syncs your AWS resources into IT Glue as configurations or flexible assets.
Each resource will have a lambda function that is either triggered by an AWS CloudWatch Event or it will be triggered on a daily basis.

The script supports the following resources from AWS:
* EC2 Instances - Instance state change triggers CloudWatch Event which triggers the lambda function. Syncs in as Configurations.
* Workspaces - Lambda function is invoked at 12:00am UTC Monday to Friday. Syncs in as Configurations.

## Requirements

You will need Python 3 installed in your system (preferably version 3.6.5)
You will also need to have aws-cli installed and configured with your AWS credentials.
* For information on installing the CLI, see [here](https://docs.aws.amazon.com/cli/latest/userguide/installing.html).
* For information on configuring your credentials see [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html).

## Getting started

##### 1. Python installation
First, you will need to make sure you have Python 3 with setuptools, pip and venv installed.
You can follow the steps [here](http://docs.python-guide.org/en/latest/starting/installation/) to install Python 3 in your system.

##### 2. Creating virtual environment
Once you have Python 3 installed, create the Python virtual environment in the root of this project with the following command:
```
python3 -m venv venv
```

##### 3. Activate virtual environment
To activate the virtual environment, use the command below that corresponds to your OS.
###### Unix or MacOS
```
source venv/bin/activate
```
###### Windows
```
venv\Scripts\activate.bat
```

##### 4. Install dependancies
Now we need to install the script dependancies using pip.
```
pip install -r requirements.txt
```
## Creating CloudFormation Stack
#### 1. Create Parameters file
Before we can create a CloudFormation stack, the script requires certain parameters to be set. Copy the `parameters_example.json` to a file named `parameters.json` at the same folder level.

In your `parameters` file, copy and paste in your IT Glue API Key, the correct API endpoint based on your region and the organization name or ID in your account where you wish to import the resources. Make sure you save before moving on to the next step.

#### 2. Create CloudFormation Stack
Now, we can create the CloudFormation stack. This will spin up a stack that contains a lambda function, a role and a policy specifically for each resource you specified to import.

- STACK_NAME - a unique name for your CloudFormation stack (required)
- --add-all - imports all the resources we currently support
- -r, --resources - takes specific resource names separated by spaces. Currently only supports 'workspace', 'ec2'. Will be ignored if --add-all flag is true.

e.g. import only workspaces
```
python create_cloudformation_stack.py STACK_NAME -r workspace
```

e.g. import all resources
```
python create_cloudformation_stack.py STACK_NAME --add-all
```
This will take a few minutes to complete. The command will terminate after the stack is completed successfully; and you can also check your AWS console to monitor the progress.

##### 3. Create lambda archive
Each lambda function created in the stack will only be functional with a lambda zip package. To zip up the packge, run:
```
python lambda_zip.py
```

##### 4. Push zip archive to lambda
Now, all we need to do is push our zip file to the Lambda. You can find all of the functions created in the stack in the `Resources` tab in the CloudFormation AWS console.

The convention of the functions are named like `ITGlueWorkspaceSyncFunction` unless changed in the template files.

```
aws lambda update-function-code --function-name <FUNCTION_NAME> --zip-file fileb://lambda_handler.zip
```

You need to repeat this for each function created in the CloudFormation stack.

### Applying changes

* If you make changes to your stack, you can change update it with the same command in step 2 with the exact same stack name.
* If you make changes to the script, you will need to repeat steps 3 and 4.


## Importing AWS Resources via Terminal
#### 1. Setting Environment Variables
The script requires your IT Glue API Key to validate requests and the IT Glue API URL
```
export ITGLUE_API_KEY=<YOUR_API_KEY>
export ITGLUE_API_URL="https://api.itglue.com"
```
For users in Europe, the API_URL is "https://api.eu.itglue.com"

#### 2. Import EC2 Instances
You can call the import scripts directly to import or update EC2 Instances. The flags available are:

* -id - imports/updates the instance that matches the instance_id
* --add-all - imports all of the EC2 instances found in AWS. Will ignore -id flag
* -il imports the locations associated with each instance

e.g. import 1 single instance without location
```
python import_ec2.py YOUR_ORG_ID  -id="INSTANCE_ID"
```

e.g. import all instances with their locations
```
python import_ec2.py YOUR_ORG_ID --add-all -il
```

#### 3.  Import Workspaces
You can call the import scripts directly to import or update workspaces. The flags available are:

* -id - imports/updates the workspace that matches the workspace_id
* --add-all - imports all of the workspaces found in your AWS account. Will ignore -id flag

e.g. import 1 single workspace
```
python import_workspace.py YOUR_ORG_ID -id="WORKSPACE_ID"
```

e.g. import all workspaces
```
python import_workspace.py YOUR_ORG_ID --add-all
```
