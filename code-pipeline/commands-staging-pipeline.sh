
# aws account id
aws sts get-caller-identity

# create ACCOUNT ID and ROLE variables
ACCOUNT_ID=<the_id>
ROLE="    - rolearn: arn:aws:iam::$ACCOUNT_ID:role/AirflowCodeBuildServiceRole\n      username: build\n      groups:\n        - system:masters"

# make the patch
kubectl get -n kube-system configmap/aws-auth -o yaml | awk "/mapRoles: \|/{print;print \"$ROLE\";next}1" > /tmp/aws-auth-patch.yml

# show the patch
cat /tmp/aws-auth-patch.yml

# apply the patch
kubectl patch configmap/aws-auth -n kube-system --patch "$(cat /tmp/aws-auth-patch.yml)"

# check
kubectl get -n kube-system configmap/aws-auth -o yaml

# create a S3 bucket for staging artifacts (choose your own as it must be unique)
aws s3 mb s3://newspedia-airflow-staging-codepipeline-artifacts

###### in post_build after pushes of the image in ECR
- echo "Testing..."
- helm upgrade --install --recreate-pods --wait --timeout 600s --namespace "staging" --set images.airflow.repository=${REPOSITORY_URI} --set images.airflow.tag=${TAG} --set executor="KubernetesExecutor" --set env[0].name="AIRFLOW__KUBERNETES__DAGS_IN_IMAGE" --set env[0].value="True" --set env[1].name="AIRFLOW__KUBERNETES__NAMESPACE" --set env[1].value="staging" --set env[2].name="AIRFLOW__KUBERNETES__WORKER_CONTAINER_REPOSITORY" --set env[2].value=${REPOSITORY_URI} --set env[3].name="AIRFLOW__KUBERNETES__WORKER_CONTAINER_TAG" --set env[3].value=${TAG} --set env[4].name="AIRFLOW__KUBERNETES__RUN_AS_USER" --set env[4].value="50000" --set env[5].name="AIRFLOW__API__AUTH_BACKEND" --set env[5].value="airflow.api.auth.backend.default" airflow-staging airflow-eks-helm-chart/airflow
- sleep 30s
- export POD_NAME=$(kubectl get pods --namespace staging -l "component=webserver,release=airflow-staging" -o jsonpath="{.items[0].metadata.name}")
- kubectl exec $POD_NAME -n staging -- /bin/bash -c "pytest integrationtests"

# deploy the stack
aws cloudformation create-stack --stack-name=newspedia-airflow-staging-pipeline --template-body=file://news-pedia/code-pipeline/airflow-staging-pipeline.cfn.yml --parameters ParameterKey=EksClusterName,ParameterValue=newspedia ParameterKey=KubectlRoleName,ParameterValue=AirflowCodeBuildServiceRole ParameterKey=GitHubUser,ParameterValue=moo-on ParameterKey=GitHubToken,ParameterValue=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 ParameterKey=GitSourceRepo,ParameterValue=newspedia-airflow-eks-docker ParameterKey=GitBranch,ParameterValue=staging
