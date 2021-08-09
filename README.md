# xrpl-price-persist-Oracle-sam


This is a XRPL Oracle that publishes external data into the XRPL.


This Oracle was inspired by
[XRPL-Labs/XRPL-Persist-Price-Oracle](https://github.com/XRPL-Labs/XRPL-Persist-Price-Oracle).
Also see [the DEV post](https://dev.to/wietse/aggregated-xrp-usd-price-info-on-the-xrp-ledger-1087).


This Oracle is coded in python and built as a [Serverless Application Model (SAM)](https://aws.amazon.com/serverless/sam/).

[**An example testnet account.**][example-testnet-account]


# Deploying to your AWS account

To deploy to your AWS Account use the `aws-sam-cli`. 
If you don't have `aws-sam-cli` installed, you can grab it from pip or follow the
[installation documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html).

```sh
pip install -U aws-sam-cli
```

After installing `aws-sam-cli`, you can **Build** and **Deploy**. 

```sh
# zip our function along with it's requirements from requirements.txt
# this also makes a new template pointing at those zips
sam build 
# now it's built, you'll be prompted to deploy, do so interactively with:
sam deploy --guided
```

This will walk you through the deployment of the Oracle, name the stack input
the parameters (the wallet seed parameter is
[`NoEcho`](#note-on-noecho-cloudformation-parameter-for-wallet-secret-seed))


Besides the one required parameter without a default (the wallet secret seed),
you can accept all the defaults (including the stack name) and you'll be persisting aggregate prices
to the XRPL Testnet. ([An example testnet account.][example-testnet-account])


After deployment, you can tail the logs of the function like, where
`my-stack-name` is what you chose to name your stack during the `--guided`
deploy, if you chose the default it's `sam-stack`:


```sh
sam logs --stack-name my-stack-name -n OracleFunction -t
```


# Note on `NoEcho` Cloudformation Parameter for Wallet Secret Seed

The `NoEcho` parameter of the wallet secret seed ensures that the parameter may
not be read or may not be logged during any cloudformation events.

The produced resource that `!Ref`'s the parameter in use, the function
with it's environment variable. Be aware that any other user able to access
the AWS account used to stand this stack will be able to read the secret on
the lambda function itself.

If you're in a trusted account, and don't provide access to tools or services
that would have access to these things you'll be fine.

Otherwise, you'll have a couple options:

One option is to encrypt the Lambda environment vars in transit (they're
encrypted at rest by default). This would then require decrypting it in the
function using a KMS call. 
(_see [Securing Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-encryption)_)

Alternatively you might want to call some key management service / secrets
management service independently.
There is two other AWS services that you could use, for managing encrypted secrets in transit.


One is Simple Systems Manager (`ssm`, specifically `ssm-encrypted`
parameter store type).
This includes some additional costs if the function needs to cold start (assuming you're
persisting the client in the outer scope for subsequent executions).
(_see [Sharing Secrets with AWS Lambda Using AWS Systems Manager Parameter Store](https://aws.amazon.com/blogs/compute/sharing-secrets-with-aws-lambda-using-aws-systems-manager-parameter-store/)_)

Another is Secrets Manager `aws-secrets-manager`, which is also an additional cost.
(_see [secretsmanager_basics.py](https://docs.aws.amazon.com/code-samples/latest/catalog/python-secretsmanager-secretsmanager_basics.py.html)_)

There are many options! This is just a minimal example :)



[example-testnet-account]: https://testnet.xrpl.org/accounts/rayZw5nJmueB5ps2bfL85aJgiKub7FsVYN "An example testnet account"
