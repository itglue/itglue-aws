cwd=$(pwd)
zip -r -X ${cwd}/lambda_handler.zip *.py
echo "Please wait, compiling packages..."
cd ${cwd}/venv/python3/lib/python3.6/site-packages/ &&  zip -q -r9 ${cwd}/lambda_handler.zip *
cd ${cwd}
aws-mfa aws lambda update-function-code --function-name ITGlueImport --zip-file fileb://${cwd}/lambda_handler.zip
rm ${cwd}/lambda_handler.zip
