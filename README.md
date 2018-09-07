# IT Glue EC2 Import Script

This script creates a lambda function in AWS which syncs your AWS EC2 instances into IT Glue as configurations.
The lambda is triggered by an AWS CloudWatch Event which is fired on an EC2 instance state change.

## Requirements

You will need Python 3 installed in your system (preferrably version 3.6.5)
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

## Importing EC2 Instances via AWS CloudFormation
##### 1. Create AWS stack
Now let's create the stack with CloudFormation using the AWS CLI tool.
```
aws cloudformation create-stack \
  --stack-name ec2synclambdastack \
  --template-body file://lambda_config.yml \
  --capabilities CAPABILITY_IAM  \
  --parameters ParameterKey=ITGlueAPIKey,ParameterValue="YOUR_API_KEY" ParameterKey=ITGlueOrganization,ParameterValue="YOUR_ORGANIZATION_NAME_OR_ID"
```

You can check your AWS console to monitor the progress of creating the stack since this can take a few minutes.

##### 2. Create lambda archive
While the stack is being created, we can take the time to create the lambda zip package.
```
python lambda_zip.py
```

##### 3. Push zip archive to lambda
Once the stack is up and running, all we need to do is push our zip file to the Lambda

```
aws lambda update-function-code --function-name ITGlueEC2SyncFunction --zip-file fileb://lambda_handler.zip
```

### Applying changes

* If you make changes to your stack, you can change update it with the AWS CLI _cloudformation update-stack_ command.
* If you make changes to the script, you will need to repeat steps 2 and 3.


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
