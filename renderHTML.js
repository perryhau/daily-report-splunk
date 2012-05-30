/**
 * Created with IntelliJ IDEA.
 * User: jakub.zygmunt
 * Date: 03/05/2012
 * Time: 16:59
 * To change this template use File | Settings | File Templates.
 */
var page = require('webpage').create(),
    fs = require('fs'),
    system = require('system'),
    domain,
    baseUrl,
    baseStaticContent,
    baseStaticContentSuffix,
    loadInProgress,
    userCookieValue,
    splunkUsername,
    splunkPassword,
    targetUrl,
    testindex = 0,
    interval,
    debug = function(msg) {

    },
    getBaseUrl = function (string) {
        var match = string.match(/(https?:\/\/([\w\.\-_]*)(?:\:[\d]+)*)\/?/),
            returnMap = { baseUrl:null, domain:null}
        if (match && match.length > 1) {
            returnMap.baseUrl = match[1];
            returnMap.domain = match[2];
        }
        return returnMap;
    },
    pushVariablesToBrowser = function (page, map) {
        setMyVar = new Function('window.myVar = ' + JSON.stringify(map));
        page.evaluate(setMyVar);
    };


page.onConsoleMessage = function (msg) {
    debug(msg);
};

page.onLoadStarted = function () {
    loadInProgress = true;
    debug("load started " );
};

page.onLoadFinished = function () {
    loadInProgress = false;
    debug("load finished.");
};


var steps = [
    function () {
        var loginUrl = baseUrl + '/en-US/account/login';
        debug('Loading ' + loginUrl);
        page.open(loginUrl);

    }, function () {
        debug('page content' + page.evaluate(function() {
            return document.body.innerHTML;
        }));
        //set cookie
        debug('Setting username / password: ');
        var myVar = {username:splunkUsername,
            password:splunkPassword
        };
        pushVariablesToBrowser(page, myVar);

        // enter the credentials
        debug('Filling the fields');
        var splunkFormLoaded = page.evaluate(function () {
            var usernameField = document.getElementById('username'),
                passwordField = document.getElementById('password'),
                isFormPresent = false;
            if (usernameField && passwordField) {
                usernameField.value = myVar.username;
                passwordField.value = myVar.password;

                var arr = document.getElementsByClassName('loginForm'), i;
                for(i=0; i < arr.length; i++) {
                    if (arr[i].getAttribute('method') == 'post') {
                        arr[i].submit();
                    }
                }

                isFormPresent = true;
            }

            return isFormPresent;
        });

        if (!splunkFormLoaded) {
            phantom.exit();
        }


    }, function () {
        debug('Load page ' + targetUrl);
        //get the report
        page.open(targetUrl);

    }, function () {
        // wait
        debug("setting up myinterval");
        loadInProgress = true;
        var myinterval = setInterval(function () {
            loadInProgress = false;
            clearInterval(myinterval);
        }, 10000);
    }, function () {
        // do cleaning through jquery code
        debug('Cleaning html');
        loadInProgress = true;
        var myVar = {webUrl:baseStaticContent};
        pushVariablesToBrowser(page, myVar);


        page.includeJs('https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js');
        page.evaluate(function () {
            var layout = $('.layout').attr('id', 'startHere'),
                length,
                logoUrl = myVar.webUrl + '/cloudreach-logo-small-transparent.png';

            if (layout.length > 0) {
                layout.html(layout.html().replace(/[ \t]+/g, ' ').replace(/[\n\r]+/g, "\n"));
                var header = $('.viewHeader', layout);
                // update src img
                $('img', layout).each(function () {
                    var t = $(this);
                    t.attr('src', logoUrl);
                });

                // remove all style attributes, remove empty divs
                var divs = $('div', layout).removeAttr('style').removeAttr('s:parentmodule').each(
                    function () {
                        var t = $(this);
                        if (t.html().trim() == '') {
                            t.remove();
                        }
                    }
                );

                // remove unused divs
                var divsToRemove = ['HiddenSavedSearch', 'HiddenPostProcess', 'JobProgressIndicator'];
                length = divsToRemove.length;
                for (var i = 0; i < length; i++) {
                    $('.' + divsToRemove[i], divs).remove();
                }
                while ((a = header.prev()).length > 0) {
                    a.remove();
                }
                header.remove();
                //            debug('exiting includeJS');
                // remove red table
                var lparents = $('.linktable', layout).parentsUntil('.layoutRow');
                $(lparents[lparents.length - 1]).remove();
                // add container_12
                $('div.layoutRow', layout).addClass('container_12').append('<div class="clear"></div>');
                $('div.layoutCell', layout).addClass('grid_12');

            }
        });
//        debug(conversionSucceed ? "conversion suceed" : "error. probably wrong session key");
        loadInProgress = false;

    },
    function () {
        debug("writing to file");
        var content = page.evaluate(function () {
                var content = document.getElementById('startHere');
                return content ? content.innerHTML : '';
            }),
            header = '<html><body><div class="container">',
//            header = fs.read('static/header.html'),
            footer = '</div></body></html>',
            dailyEmail = header + content + footer;
        if (content !== '') {
            console.log(dailyEmail);
        } else {
            debug('Content is empty');
        }

    }
];
if (phantom.args.length > 3) {
    targetUrl = phantom.args[0];
    baseStaticContentSuffix = phantom.args[1];
//    userCookieValue = phantom.args[2];
    splunkUsername = phantom.args[2];
    splunkPassword = phantom.args[3]
    var urlMap = getBaseUrl(targetUrl);
    baseUrl = urlMap.baseUrl;
    baseStaticContent = baseUrl + baseStaticContentSuffix;
    domain = urlMap.domain;

    if (phantom.args.length > 4) {
        console.log('Enabling debug');
        // more than 2 arguments - debugmode!!!
        debug = function( msg ) {
            console.log(msg);
        }
    }

    interval = setInterval(function () {
        if (!loadInProgress && typeof steps[testindex] == "function") {
            debug('Step ' + testindex);
            steps[testindex]();
            testindex++;
        }
        if (typeof steps[testindex] != "function") {
            phantom.exit();
        }
    }, 50);
} else {
    phantom.exit();
}
