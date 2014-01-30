var app = angular.module('project', ['ngRoute']);

app.config(['$routeProvider',
  function($routeProvider) {
    $routeProvider.
      when('/', {
        templateUrl: static_url + 'yaccounts/partials/api_keys.html',
        controller: 'ApiKeysCtrl'
      }).
      otherwise({
        redirectTo: '/'
      });
  }
]);
 
function ApiKeysCtrl($scope) {
}