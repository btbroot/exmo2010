/*
Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
Copyright 2013 Al Nikolov
Copyright 2013 Foundation "Institute for Information Freedom Development"
For licensing, see LICENSE.html or http://ckeditor.com/license
*/

CKEDITOR.editorConfig = function( config )
{
	// Define changes to default configuration here. For example:
	// config.language = 'fr';
	// config.uiColor = '#AADC6E';
};

CKEDITOR.on('dialogDefinition', function(event) {
    // Take the dialog name and its definition from the event data.
    var dialogName = event.data.name;
    var dialogDefinition = event.data.definition;

    // Check if the definition is from the dialog we're interested in (the 'link' dialog).
    if (dialogName == 'link') {

        // Get a reference to the "Target" tab and set default to '_blank'
        var targetTab = dialogDefinition.getContents('target');
        var targetField = targetTab.get('linkTargetType');
        targetField['default'] = '_blank';

    }
});
