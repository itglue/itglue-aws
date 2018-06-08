# IT Glue EC2 Import Script

This script creates a lambda function in AWS which syncs your AWS EC2 instances into IT Glue as configurations.
The lambda is triggered by an AWS CloudWatch Event which is fired on an EC2 instance state change.

## Requirements

You will need Python installed in your system (preferrably version 3.6.5)
You will also need to have aws-cli installed and configured with your AWS credentials.
* For information on installing the CLI, see [here](https://docs.aws.amazon.com/cli/latest/userguide/installing.html).
* For information on configuring your credentials see [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html).

## Getting started

First, let's create your Python environment
```
python3 -m venv venv
```
And then activate it
####### Unix or MacOS
```
source venv/bin/activate
```
###### Windows
```
venv\Scripts\activate.bat
```

Now we need to install the dependancies
```
pip install -r requirements.txt
```

Once we have all the dependancies installed, we can create the lambda zip package
```
python lambda_zip.py
```

Now let's create the stack with CloudFormation using the AWS CLI tool
```
aws cloudformation create-stack \
  --stack-name ec2synclambdastack \
  --template-body file://lambda_config.yml \
  --capabilities CAPABILITY_IAM  \
  --parameters ParameterKey=ITGlueAPIKey,ParameterValue="YOUR_API_KEY" ParameterKey=ITGlueOrganization,ParameterValue="YOUR_ORGANIZATION_NAME_OR_ID"
```

You can check your AWS console to monitor the progress of creating the stack since this can take a few minutes.
Once the stack is up and running, all we need to do is push our zip file to the Lambda

```
aws lambda update-function-code --function-name ITGlueEC2SyncFunction --zip-file fileb://lambda_handler.zip
```
