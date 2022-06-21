# Create the S3 bucket for the CodePipeline artifacts - This bucket must be globally unique so set your own
aws s3 mb s3://newspedia-airflow-dev-codepipeline-artifacts

# Create IAM roles and add iniline policies so that CodePipeline can interact with EKS through kubectl
aws iam create-role --role-name AirflowCodePipelineServiceRole --assume-role-policy-document file://news-pedia/code-pipeline/cpAssumeRolePolicyDocument.json
aws iam put-role-policy --role-name AirflowCodePipelineServiceRole --policy-name codepipeline-access --policy-document file://news-pedia/code-pipeline/cpPolicyDocument.json
aws iam create-role --role-name AirflowCodeBuildServiceRole --assume-role-policy-document file://news-pedia/code-pipeline/cbAssumeRolePolicyDocument.json
aws iam put-role-policy --role-name AirflowCodeBuildServiceRole --policy-name codebuild-access --policy-document file://news-pedia/code-pipeline/cbPolicyDocument.json

# open the flux pipeline to set the bucket name you created under "ArtifactStore"
vim airflow-materials-aws/code-pipeline/airflow-dev-pipeline.cfn.yml

# Create the AWS CodePipeline using CloudFormation (This doesn't deploy the image as Flux handles it)
aws cloudformation create-stack --stack-name=newspedia-airflow-dev-pipeline --template-body=file://news-pedia/code-pipeline/airflow-dev-pipeline.cfn.yml --parameters ParameterKey=GitHubUser,ParameterValue=moo-on ParameterKey=GitHubToken,ParameterValue=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 ParameterKey=GitSourceRepo,ParameterValue=newspedia-airflow-eks-docker ParameterKey=GitBranch,ParameterValue=dev

aws s3 mb s3://newspedia-flask-dev-codepipeline-artifacts

aws cloudformation create-stack --stack-name=newspedia-flask-dev-pipeline --template-body=file://news-pedia/code-pipeline/flask-dev-pipeline.cfn.yml --parameters ParameterKey=GitHubUser,ParameterValue=moo-on ParameterKey=GitHubToken,ParameterValue=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 ParameterKey=GitSourceRepo,ParameterValue=newspedia-flask-eks-docker ParameterKey=GitBranch,ParameterValue=dev