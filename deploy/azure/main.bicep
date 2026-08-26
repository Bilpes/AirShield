targetScope = 'subscription'

@description('Short lowercase deployment prefix.')
@minLength(3)
@maxLength(12)
param prefix string
param location string = 'swedencentral'
param tenantId string
@secure()
param postgresAdminPassword string
@secure()
@description('Complete asyncpg URL; stored in Key Vault for CSI synchronization.')
param databaseUrl string
@secure()
@description('Base64-encoded random HMAC key of at least 32 bytes.')
param tokenIndexKeyB64 string
@secure()
@minLength(32)
param edgeGatewaySharedSecret string
@secure()
@minLength(32)
param edgeGatewayPreviousSecret string
param kubernetesVersion string = '1.32'
param postgresGeoRedundantBackup bool = true

var resourceGroupName = '${prefix}-airshield-rg'
var tags = { workload: 'airshield', dataClassification: 'restricted', managedBy: 'bicep' }

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module platform 'platform.bicep' = {
  scope: rg
  name: 'airshield-platform'
  params: {
    prefix: prefix
    location: location
    tenantId: tenantId
    postgresAdminPassword: postgresAdminPassword
    databaseUrl: databaseUrl
    tokenIndexKeyB64: tokenIndexKeyB64
    edgeGatewaySharedSecret: edgeGatewaySharedSecret
    edgeGatewayPreviousSecret: edgeGatewayPreviousSecret
    kubernetesVersion: kubernetesVersion
    postgresGeoRedundantBackup: postgresGeoRedundantBackup
    tags: tags
  }
}

output resourceGroupName string = rg.name
output aksName string = platform.outputs.aksName
output keyVaultName string = platform.outputs.keyVaultName
output gatewayKeyVaultName string = platform.outputs.gatewayKeyVaultName
output workloadIdentityClientId string = platform.outputs.workloadIdentityClientId
output webIdentityClientId string = platform.outputs.webIdentityClientId
output edgeIdentityClientId string = platform.outputs.edgeIdentityClientId
output gatewayIdentityClientId string = platform.outputs.gatewayIdentityClientId
output oidcIssuer string = platform.outputs.oidcIssuer
