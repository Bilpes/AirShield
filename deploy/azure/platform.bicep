param prefix string
param location string
param tenantId string
@secure()
param postgresAdminPassword string
@secure()
param databaseUrl string
@secure()
param tokenIndexKeyB64 string
@secure()
param edgeGatewaySharedSecret string
@secure()
param edgeGatewayPreviousSecret string
param kubernetesVersion string
param postgresGeoRedundantBackup bool
param tags object

var unique = toLower(uniqueString(resourceGroup().id))
var keyVaultName = take('${prefix}askv${unique}', 24)
var gatewayVaultName = take('${prefix}asgw${unique}', 24)
var aksName = '${prefix}-airshield-aks'
var postgresName = '${prefix}-airshield-pg-${unique}'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-airshield-logs'
  location: location
  tags: tags
  properties: { retentionInDays: 365, features: { enableLogAccessUsingOnlyResourcePermissions: true } }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: '${prefix}-airshield-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.20.0.0/16'] }
    subnets: [
      { name: 'aks', properties: { addressPrefix: '10.20.0.0/22', privateEndpointNetworkPolicies: 'Disabled' } }
      { name: 'postgres', properties: { addressPrefix: '10.20.4.0/24', delegations: [{ name: 'postgres', properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' } }] } }
      { name: 'private-endpoints', properties: { addressPrefix: '10.20.5.0/24', privateEndpointNetworkPolicies: 'Disabled' } }
    ]
  }
}

resource aksSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-01-01' existing = { parent: vnet, name: 'aks' }
resource pgSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-01-01' existing = { parent: vnet, name: 'postgres' }
resource peSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-01-01' existing = { parent: vnet, name: 'private-endpoints' }

resource workloadIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-airshield-workload'
  location: location
  tags: tags
}

resource webIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-airshield-web'
  location: location
  tags: tags
}

resource edgeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-airshield-edge'
  location: location
  tags: tags
}

resource gatewayIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-airshield-gateway'
  location: location
  tags: tags
}

resource aks 'Microsoft.ContainerService/managedClusters@2024-05-01' = {
  name: aksName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    kubernetesVersion: kubernetesVersion
    dnsPrefix: aksName
    enableRBAC: true
    disableLocalAccounts: true
    publicNetworkAccess: 'Disabled'
    oidcIssuerProfile: { enabled: true }
    securityProfile: { workloadIdentity: { enabled: true }, defender: { logAnalyticsWorkspaceResourceId: workspace.id, securityMonitoring: { enabled: true } } }
    apiServerAccessProfile: { enablePrivateCluster: true, enablePrivateClusterPublicFQDN: false }
    aadProfile: { managed: true, enableAzureRBAC: true, tenantID: tenantId }
    networkProfile: { networkPlugin: 'azure', networkPluginMode: 'overlay', networkPolicy: 'azure', loadBalancerSku: 'standard', outboundType: 'managedNATGateway', natGatewayProfile: { managedOutboundIPProfile: { count: 1 }, idleTimeoutInMinutes: 10 }, serviceCidr: '10.21.0.0/16', dnsServiceIP: '10.21.0.10' }
    agentPoolProfiles: [{ name: 'system', mode: 'System', count: 3, vmSize: 'Standard_D4ds_v5', osType: 'Linux', osSKU: 'AzureLinux', vnetSubnetID: aksSubnet.id, enableAutoScaling: true, minCount: 3, maxCount: 9, availabilityZones: ['1', '2', '3'], maxPods: 50, type: 'VirtualMachineScaleSets' }]
    autoUpgradeProfile: { upgradeChannel: 'stable', nodeOSUpgradeChannel: 'NodeImage' }
    addonProfiles: { azureKeyvaultSecretsProvider: { enabled: true, config: { enableSecretRotation: 'true', rotationPollInterval: '2m' } }, omsagent: { enabled: true, config: { logAnalyticsWorkspaceResourceID: workspace.id } } }
  }
}

resource federation 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: workloadIdentity
  name: 'airshield-control-plane'
  properties: {
    issuer: aks.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:airshield:airshield-control-plane'
    audiences: ['api://AzureADTokenExchange']
  }
}

resource webFederation 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: webIdentity
  name: 'airshield-web'
  properties: {
    issuer: aks.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:airshield:airshield-web'
    audiences: ['api://AzureADTokenExchange']
  }
}

resource edgeFederation 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: edgeIdentity
  name: 'airshield-edge'
  properties: {
    issuer: aks.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:airshield:airshield-edge'
    audiences: ['api://AzureADTokenExchange']
  }
}

resource gatewayFederation 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: gatewayIdentity
  name: 'airshield-gateway'
  properties: {
    issuer: aks.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:airshield:airshield-gateway'
    audiences: ['api://AzureADTokenExchange']
  }
}

resource postgresDns 'Microsoft.Network/privateDnsZones@2024-06-01' = { name: 'private.postgres.database.azure.com', location: 'global', tags: tags }
resource postgresDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = { parent: postgresDns, name: 'airshield-vnet', location: 'global', properties: { registrationEnabled: false, virtualNetwork: { id: vnet.id } } }
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresName
  location: location
  tags: tags
  sku: { name: 'Standard_D4ds_v5', tier: 'GeneralPurpose' }
  properties: {
    version: '16'
    administratorLogin: 'airshield_admin'
    administratorLoginPassword: postgresAdminPassword
    network: { publicNetworkAccess: 'Disabled', delegatedSubnetResourceId: pgSubnet.id, privateDnsZoneArmResourceId: postgresDns.id }
    storage: { storageSizeGB: 256, autoGrow: 'Enabled' }
    backup: { backupRetentionDays: 35, geoRedundantBackup: postgresGeoRedundantBackup ? 'Enabled' : 'Disabled' }
    highAvailability: { mode: 'ZoneRedundant' }
    authConfig: { activeDirectoryAuth: 'Enabled', passwordAuth: 'Enabled', tenantId: tenantId }
  }
  dependsOn: [postgresDnsLink]
}
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = { parent: postgres, name: 'airshield', properties: { charset: 'UTF8', collation: 'en_US.utf8' } }

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: { tenantId: tenantId, sku: { family: 'A', name: 'premium' }, enableRbacAuthorization: true, enablePurgeProtection: true, enableSoftDelete: true, softDeleteRetentionInDays: 90, publicNetworkAccess: 'Disabled', networkAcls: { bypass: 'AzureServices', defaultAction: 'Deny' } }
}
resource wrapKey 'Microsoft.KeyVault/vaults/keys@2023-07-01' = { parent: keyVault, name: 'airshield-wrap', properties: { kty: 'RSA-HSM', keySize: 3072, keyOps: ['wrapKey', 'unwrapKey'], attributes: { enabled: true, exportable: false } } }
resource signKey 'Microsoft.KeyVault/vaults/keys@2023-07-01' = { parent: keyVault, name: 'airshield-receipt-sign', properties: { kty: 'RSA-HSM', keySize: 3072, keyOps: ['sign', 'verify'], attributes: { enabled: true, exportable: false } } }
resource databaseSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = { parent: keyVault, name: 'database-url', properties: { value: databaseUrl } }
resource tokenIndexSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = { parent: keyVault, name: 'token-index-key-b64', properties: { value: tokenIndexKeyB64 } }
resource cryptoRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = { name: guid(keyVault.id, workloadIdentity.id, 'crypto-user'), scope: keyVault, properties: { principalId: workloadIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '12338af0-0e69-4776-bea7-57ae8d297424') } }
resource secretRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = { name: guid(keyVault.id, workloadIdentity.id, 'secrets-user'), scope: keyVault, properties: { principalId: workloadIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') } }

resource gatewayVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: gatewayVaultName
  location: location
  tags: tags
  properties: { tenantId: tenantId, sku: { family: 'A', name: 'standard' }, enableRbacAuthorization: true, enablePurgeProtection: true, enableSoftDelete: true, softDeleteRetentionInDays: 90, publicNetworkAccess: 'Disabled', networkAcls: { bypass: 'AzureServices', defaultAction: 'Deny' } }
}
resource edgeGatewaySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = { parent: gatewayVault, name: 'edge-gateway-shared-secret', properties: { value: edgeGatewaySharedSecret } }
resource edgeGatewayPreviousSecretResource 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = { parent: gatewayVault, name: 'edge-gateway-previous-secret', properties: { value: edgeGatewayPreviousSecret } }
resource gatewaySecretRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = { name: guid(gatewayVault.id, gatewayIdentity.id, 'secrets-user'), scope: gatewayVault, properties: { principalId: gatewayIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') } }

resource vaultDns 'Microsoft.Network/privateDnsZones@2024-06-01' = { name: 'privatelink.vaultcore.azure.net', location: 'global', tags: tags }
resource vaultDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = { parent: vaultDns, name: 'airshield-vnet', location: 'global', properties: { registrationEnabled: false, virtualNetwork: { id: vnet.id } } }
resource vaultEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = { name: '${prefix}-kv-pe', location: location, tags: tags, properties: { subnet: { id: peSubnet.id }, privateLinkServiceConnections: [{ name: 'vault', properties: { privateLinkServiceId: keyVault.id, groupIds: ['vault'] } }] } }
resource vaultDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = { parent: vaultEndpoint, name: 'default', properties: { privateDnsZoneConfigs: [{ name: 'vault', properties: { privateDnsZoneId: vaultDns.id } }] } }
resource gatewayVaultEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = { name: '${prefix}-gateway-kv-pe', location: location, tags: tags, properties: { subnet: { id: peSubnet.id }, privateLinkServiceConnections: [{ name: 'vault', properties: { privateLinkServiceId: gatewayVault.id, groupIds: ['vault'] } }] } }
resource gatewayVaultDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = { parent: gatewayVaultEndpoint, name: 'default', properties: { privateDnsZoneConfigs: [{ name: 'vault', properties: { privateDnsZoneId: vaultDns.id } }] } }

resource kvDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = { scope: keyVault, name: 'airshield', properties: { workspaceId: workspace.id, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] } }
resource gatewayKvDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = { scope: gatewayVault, name: 'airshield', properties: { workspaceId: workspace.id, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] } }
resource pgDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = { scope: postgres, name: 'airshield', properties: { workspaceId: workspace.id, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] } }

output aksName string = aks.name
output keyVaultName string = keyVault.name
output gatewayKeyVaultName string = gatewayVault.name
output workloadIdentityClientId string = workloadIdentity.properties.clientId
output webIdentityClientId string = webIdentity.properties.clientId
output edgeIdentityClientId string = edgeIdentity.properties.clientId
output gatewayIdentityClientId string = gatewayIdentity.properties.clientId
output oidcIssuer string = aks.properties.oidcIssuerProfile.issuerURL
