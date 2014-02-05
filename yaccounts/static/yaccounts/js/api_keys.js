var app = angular.module('project', ['ngCookies', 'ngResource']);

app.run(function($rootScope, $http, $cookies){
    // Set Django CSRF token.
    $http.defaults.xsrfCookieName = 'csrftoken';
    $http.defaults.xsrfHeaderName = 'X-CSRFToken';
});
 
function ApiKeysCtrl($scope, $http, $resource) {

    // Fetch user's API Keys.
    var APIKeys = $resource(api_keys_api_url + '/:id', { id: '@id' }, {
        'update': { method: 'PUT' }
    });
    var apiKeysList = APIKeys.query(function() {
        $scope.apiKeys = apiKeysList;
    });

    // Create new API Key.
    $scope.newApiKey = function() {
        var description = prompt('Description');
        if(description) {
            APIKeys.save(null,
                { description: description },
                function success(value, responseHeaders) {
                    $scope.apiKeys.push(value);
                },
                function error(httpResponse) {
                    alert('Error creating API Key');
                }
            );
        }
    };

    // Set active.
    $scope.setActive = function(apiKey, value) {
        apiKey.active = value;
        apiKey.$update();
    };

    // Edit description.
    $scope.editDescription = function(apiKey) {
        apiKey.description = prompt('Enter Description', apiKey.description);
        apiKey.$update();
    };

    // Delete API Key.
    $scope.destroy = function(apiKey) {
        if(confirm('Are you sure?')) {
            apiKey.$delete();
            $scope.apiKeys.splice(apiKey, 1);
        }
    };
}