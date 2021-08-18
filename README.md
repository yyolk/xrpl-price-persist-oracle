# xrpl-price-persist-oracle-sam

## Mainnet

💳: `rEGGDggxupqxJ3ZbDTLUzKtpHxHyhtUtiU`
[🧭][mainnet-account-xrplf]

▶️: [![Mainnet](https://github.com/yyolk/xrpl-price-persist-oracle-sam/actions/workflows/mainnet.yml/badge.svg)](https://github.com/yyolk/xrpl-price-persist-oracle-sam/actions/workflows/mainnet.yml)


## Testnet

💳: `rayZw5nJmueB5ps2bfL85aJgiKub7FsVYN`
[🧭][testnet-account-xrplf]

▶️: [![Testnet](https://github.com/yyolk/xrpl-price-persist-oracle-sam/actions/workflows/testnet.yml/badge.svg)](https://github.com/yyolk/xrpl-price-persist-oracle-sam/actions/workflows/testnet.yml)


## Price via Oracle

<div align="center">

![price USD PT-3H](https://d1nfdw5fckjov0.cloudfront.net/price_pt3h_line.png)

![price USD PT-1D](https://d1nfdw5fckjov0.cloudfront.net/price_pt1d_line.png)
 
<details><summary> This shows the Testnet updates less frequently than the mainnet. </summary>

![price USD PT-3H Mainnet & Testnet](https://d1nfdw5fckjov0.cloudfront.net/price_pt3h_line_allnets.png)

</details>

</div>

This is a XRPL Oracle that publishes external data into the XRPL.


This Oracle was inspired by
[XRPL-Labs/XRPL-Persist-Price-Oracle](https://github.com/XRPL-Labs/XRPL-Persist-Price-Oracle).
Also see [the DEV post](https://dev.to/wietse/aggregated-xrp-usd-price-info-on-the-xrp-ledger-1087).


This Oracle is coded in python and built as a [Serverless Application Model (SAM)](https://aws.amazon.com/serverless/sam/).

Take a look at the `handler()` in [`contract.py`](oracle/contract.py) &mdash; where it's expected to run on any [FaaS](https://en.wikipedia.org/wiki/Function_as_a_service), such as [OpenFaaS](https://github.com/openfaas/faas).


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

<details>
<summary>

*Don't feel like doing it yourself? Expand me to see termcasts.*

</summary>

1. New stack, accepting all the defaults, besides the wallet secret.
  - [![asciicast](https://asciinema.org/a/rLjmZcKyQXGCXe4gc2AP62Pyd.svg)](https://asciinema.org/a/rLjmZcKyQXGCXe4gc2AP62Pyd)
2. A current stack, getting updated and deployed to
  - [![asciicast](https://asciinema.org/a/w6Mhzh67fnswTdtwKA8KLJdOG.svg)](https://asciinema.org/a/w6Mhzh67fnswTdtwKA8KLJdOG)

</details>

This will walk you through the deployment of the Oracle, name the stack input
the parameters (the wallet seed parameter is
[`NoEcho`](#note-on-noecho-cloudformation-parameter-for-wallet-secret-seed))

You may generate a Testnet wallet at the Testnet faucet: https://xrpl.org/xrp-testnet-faucet.html
Click "Generate Testnet Credentials" and use the **Secret** as
the input to the `WalletSecret` parameter.


Besides the one required parameter without a default (the wallet secret seed),
you can accept all the defaults (including the stack name) and you'll be persisting aggregate prices
to the XRPL Testnet.


# Tailing Logs

After deployment, you can tail the logs of the function like, where
`my-stack-name` is what you chose to name your stack during the `--guided`
deploy, if you chose the default it's `sam-app`:


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

You'll want to attach a policy to the function like in [`5603945`](https://github.com/yyolk/xrpl-price-persist-oracle-sam/blob/c8982dddf080b0cf6a75907aad0467dc9e3b8dd4/template.yaml#L93-L95)
include a policy attached to the `OracleFunction` resource under the
`Properties` dict.


```yaml
    Properties:
      CodeUri: oracle/
      Handler: contract.handler
      Runtime: python3.8
      Policies:
        - SSMParameterReadPolicy:
            # this should be a path you decide, here's an example:
            ParameterName: xrpl-oracle/test/wallet/secret
            # you can also use `!Sub`:
            # ParameterName: !Sub "xrpl-oracle/${XRPLNodeEnvironment}/wallet/secret"
```

Another is Secrets Manager `aws-secrets-manager`, which is also an additional cost.
(_see [secretsmanager_basics.py](https://docs.aws.amazon.com/code-samples/latest/catalog/python-secretsmanager-secretsmanager_basics.py.html)_)

There are many options! This is just a minimal example :)



[mainnet-account-xrplf]: https://explorer.xrplf.org/rEGGDggxupqxJ3ZbDTLUzKtpHxHyhtUtiU "rEGGDggxupqxJ3ZbDTLUzKtpHxHyhtUtiU"
[testnet-account-xrplf]: https://explorer-testnet.xrplf.org/rayZw5nJmueB5ps2bfL85aJgiKub7FsVYN "rayZw5nJmueB5ps2bfL85aJgiKub7FsVYN"
[example-testnet-account]: https://testnet.xrpl.org/accounts/rayZw5nJmueB5ps2bfL85aJgiKub7FsVYN "An example testnet account"
