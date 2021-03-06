/**
 * @fileoverview This is a visualizer for the pirate game.
 * @author <a href="mailto:marco.leise@gmx.de">Marco Leise</a>
 */

// TODO: FEAT: info button showing a message box with game meta data
// TODO: FEAT: menu items: toggle graph/score bars, cpu use
// TODO: FEAT: setting for cpu usage
// TODO: NICE: better player rank display
// TODO: COSMETIC: draw only visible pirates when zoomed in
/**
 * @namespace Enum for the different states, the visualizer can be in.
 */
LoadingState = {
	/**
	 * The visualizer is not currently loading a replay or map.
	 *
	 * @const
	 */
	IDLE : 0,
	/**
	 * The visualizer is loading a replay or map and cannot take any load requests.
	 *
	 * @const
	 */
	LOADING : 1,
	/**
	 * The visualizer is currently cleaning up.
	 *
	 * @const
	 * @see Visualizer#cleanUp
	 */
	CLEANUP : 2
};

/**
 * @class The main 'application' object that provides all necessary methods for the use in a web
 *        page. Usually you just construct an instance and then call
 *        {@link Visualizer#loadReplayData} or {@link Visualizer#loadReplayDataFromURI}.
 * @constructor
 * @param {Node}
 *        container the HTML element, that the visualizer will embed into
 * @param {Options}
 *        options Adds immutable options. These can be overridden via URL parameters. The visualizer
 *        will not copy this {@link Options} instance, but instead use it directly. Modifications to
 *        the object at a later point will result in undefined behavior.
 * @param {Number}
 *        w an optional maximum width or undefined
 * @param {Number}
 *        h an optional maximum height or undefined
 * @param {Object}
 *        configOverrides an optional configuration; each field overrides the respective value in
 *        the user's configuration or the default; see {@link Config} for possible options
 */
Visualizer = function(container, options, w, h, configOverrides) {
	var parameters, equalPos, value, i, text, imgDir;
	var key = undefined;
	var vis = this;
	/** @private */
	this.loading = LoadingState.LOADING;
	/*
	 * First of all get our logging up and running, so we can print possible error messages.
	 */
	/** @private */
	this.container = container;
	while (container.hasChildNodes()) {
		container.removeChild(container.lastChild);
	}
	/** @private */
	this.log = document.createElement('div');
	this.container.appendChild(this.log);

	// proceed with initialization
	try {
		/** @private */
		this.state = new State();
		/** @private */
		this.map = new CanvasElementMap(this.state);
		/** @private */
		this.piratesMap = new CanvasElementPiratesMap(this.state, this.map);
		/** @private */
		this.shiftedMap = new CanvasElementShiftedMap(this.state, this.piratesMap);
		/** @private */
		this.turns = undefined;
		/** @private */
		this.w = w;
		/** @private */
		this.h = h;
		if (configOverrides) this.state.config.overrideFrom(configOverrides);
		/** @private */
		this.state.options = options;
		if (!this.state.options.playercolors) {
            this.state.options.playercolors = ['#b30000', '#4d4dff', '#030303']; // previous: '#2E3192', '#E96E31', '#030303'
		}
		if (this.state.options.bigscreen) {
			this.state.config.slowDown = true;
		}
        var color1 = this.state.options.color1;
        var color2 = this.state.options.color2;
        // read URL parameters and store them in the parameters object
		parameters = window.location.href;
		if ((i = parameters.indexOf('?')) !== -1) {
			parameters = parameters.substr(i + 1).split('#')[0].split('&');
			for (i = 0; i < parameters.length; i++) {
				equalPos = parameters[i].indexOf('=');
				key = parameters[i].substr(0, equalPos);
				value = parameters[i].substr(equalPos + 1);
				switch (key) {
				case 'debug':
					this.state.options['debug'] = Options.toBool(value);
					break;
				case 'interactive':
					this.state.options['interactive'] = Options.toBool(value);
					break;
				case 'profile':
					this.state.options['profile'] = Options.toBool(value);
					break;
				case 'decorated':
					this.state.options['decorated'] = Options.toBool(value);
					break;
				case 'col':
					this.state.options['col'] = parseInt(value);
					break;
				case 'row':
					this.state.options['row'] = parseInt(value);
					break;
				case 'turn':
					this.state.options['turn'] = parseInt(value);
					break;
				case 'data_dir':
					this.state.options['data_dir'] = value;
					break;
				case 'game':
					this.state.options['game'] = value;
					break;
				case 'user':
					this.state.options['user'] = value;
					break;
				case 'config':
					this.state.config.overrideFrom(JSON.parse(unescape(value)));
				}
			}
		}
		// set default zoom to max if we are going to zoom in on a square
		if (!isNaN(this.state.options['row']) && !isNaN(this.state.options['col'])) {
			this.state.config['zoom'] = 1 << Math.ceil(Math.log(ZOOM_SCALE) / Math.LN2);
		}
        imgDir = (this.state.options['data_dir'] || '') + 'img/';
		/** @private */
		this.imgMgr = new ImageManager(imgDir, new Delegate(this, this.completedImages));

		/* Do not load boards on the site */
        this.imgMgr.put('boardA', 'water.png');
        /*this.imgMgr.put('boardA', 'Skills_Pirates_Website_Map_Water_A.png');
		this.imgMgr.put('boardB', 'Skills_Pirates_Website_Map_Water_B.png');
		this.imgMgr.put('boardC', 'Skills_Pirates_Website_Map_Water_C.png');
        */
		this.imgMgr.put('treasure_v1', 'coins.png');
		this.imgMgr.put('treasure_v2', 'Pearl.png');
		this.imgMgr.put('treasure_v3', 'GoldenBlock.png');
		this.imgMgr.put('treasure_v4', 'Grail.png');
		this.imgMgr.put('treasure_v5', 'Diamond.png');
		this.imgMgr.put('treasure_v6', 'Crown.png');
		this.imgMgr.put('ship_p1', 'Ships/Ship_' + color1 + '.png');
		this.imgMgr.put('ship_p2', 'Ships/Ship_' + color2 + '.png');
		this.imgMgr.put('drunk', '4-Ships_drunk.png');
		this.imgMgr.put('treasure_on_shipV1', '4-Ships_coins.png');
		this.imgMgr.put('treasure_on_shipV2', '4-Ships_Pearl.png');
		this.imgMgr.put('treasure_on_shipV3', '4-Ships_Gold-Block.png');
		this.imgMgr.put('treasure_on_shipV4', '4-Ships_Grail.png');
		this.imgMgr.put('treasure_on_shipV5', '4-Ships_Diamond.png');
		this.imgMgr.put('treasure_on_shipV6', '4-Ships_Crown.png');
		this.imgMgr.put('barrel', 'barrel_flip.png');
		this.imgMgr.put('ship_defend', '4-Ships_defend.png');

		this.imgMgr.put('speed_powerup', 'speed_powerup.png');
		this.imgMgr.put('ship_with_speed_powerup', '4-Ships_Speed-Ship-s.png');
		this.imgMgr.put('attack_powerup', 'attack_powerup.png');
		this.imgMgr.put('ship_with_attack_powerup', '4-Ships_Attack-Ship-s.png');

		this.imgMgr.put('script', 'Script.png');
		this.imgMgr.put('script2', 'Script2.png');

        /** @private */
		this.director = new Director(this);
		/** @private */
		this.mouseX = -1;
		/** @private */
		this.mouseY = -1;
		/** @private */
		this.mouseDown = 0;
		/** @private */
		this.progressList = [];

		// print out the configuration
		text = 'Loading visualizer...';
		text += Html.table(function() {
			var table = '';
			var key = undefined;
			for (key in vis.options) {
				var value = vis.options[key];
				table += Html.tr(function() {
					return Html.td(function() {
						return Html.bold(key);
					}) + Html.td(value) + Html.td(function() {
						var result = '<i>';
						if (key === 'data_dir') result += '(Image directory)';
						return result + '</i>';
					});
				});
			}
			return table;
		});
		this.log.innerHTML = text;

		/** @private */
		this.replayStr = undefined;
		/** @private */
		this.replayReq = undefined;
		/**
		 * the main canvas
		 *
		 * @private
		 */
		this.main = {};
		/**
		 * a hint text overlay
		 *
		 * @private
		 */
		this.hint = '';

		// start loading images in the background and wait
		this.loading = LoadingState.IDLE;
		this.imgMgr.startRequests();
	} catch (error) {
		this.exceptionOut(error, false);
		throw error;
	}
};

/**
 * Prints a message on the screen and then executes a function. Usually the screen is not updated
 * until the current thread of execution has finished. To work around that limitation, this method
 * adds the function to be called to the browser's timer queue. Additionally any thrown errors are
 * also printed.
 *
 * @private
 * @param {String}
 *        log a message to be logged before executing the function
 * @param {Function}
 *        func a function to be called after displaying the message
 * @param {String}
 *        id An identification of the progress that will be used to filter duplicates in the queue.
 */
Visualizer.prototype.progress = function(log, func, id) {
	var i;
	if (this.loading !== LoadingState.LOADING) return;
	for (i = 0; i < this.progressList.length; i++) {
		if (id === this.progressList[i]) return;
	}
	this.progressList.push(id);
	var vis = this;
	if (log) this.logOut(log);
	window.setTimeout(function() {
		var k;
		func();
		for (k = 0; k < vis.progressList.length; k++) {
			if (id === vis.progressList[k]) {
				vis.progressList.splice(k, 1);
				break;
			}
		}
	}, 50);
};

/**
 * Places a paragraph with a message in the visualizer DOM element.
 *
 * @private
 * @param {String}
 *        text the message text
 */
Visualizer.prototype.logOut = function(text) {
	this.log.innerHTML += text.replace(/\n/g, '<br>') + '<br>';
};

/**
 * Stops loading, cleans up the instance and calls {@link Visualizer#logOut} with the text in red.
 *
 * @private
 * @param {string}
 *        text the error message text
 * @param {Boolean}
 *        cleanUp whether the visualizer should try to reset itself; this is only useful if the
 *        error is not coming from the constructor.
 */
Visualizer.prototype.errorOut = function(text, cleanUp) {
	this.logOut('<font style="color:red">' + text + '</font>');
	if (cleanUp) this.cleanUp();
};

/**
 * Converts a JavaScript Error into a HTML formatted string representation and prints that on the
 * web page.
 *
 * @private
 * @param {Error|String}
 *        error a thrown error or string
 * @param {Boolean}
 *        cleanUp whether the visualizer should try to reset itself; this is only useful if the
 *        error is not coming from the constructor.
 */
Visualizer.prototype.exceptionOut = function(error, cleanUp) {
    this.errorOut(error, cleanUp);
    throw new Error(error);
};

/**
 * Resets the visualizer and associated objects to an initial state. This method is also called in
 * case of an error.
 *
 * @private
 */
Visualizer.prototype.cleanUp = function() {
	this.loading = LoadingState.CLEANUP;
	if (this.replayReq) this.replayReq.abort();
	if (this.state.options['decorated']) {
		this.imgMgr.cleanUp();
	}
	this.director.cleanUp();
	this.state.cleanUp();
	this.replayStr = undefined;
	this.replayReq = undefined;
	if (this.main.canvas) {
		if (this.container.firstChild === this.main.canvas) {
			this.container.removeChild(this.main.canvas);
		}
	}
	document.onkeydown = null;
	document.onkeyup = null;
	document.onkeypress = null;
	window.onresize = null;
	this.log.style.display = 'block';
};

/**
 * This is called before a replay or map is loaded to ensure the visualizer is in an idle state at
 * that time. It then sets the state to {@link LoadingState}.LOADING.
 *
 * @private
 * @returns {Boolean} true, if the visualizer was idle.
 */
Visualizer.prototype.preload = function() {
	if (this.loading !== LoadingState.IDLE) return true;
	this.cleanUp();
	this.loading = LoadingState.LOADING;
	return false;
};

/**
 * Loads a replay string directly.
 *
 * @param {string}
 *        data the replay string
 */
Visualizer.prototype.loadReplayData = function(data) {
	if (this.preload()) return;
	this.replayStr = data;
	this.loadCanvas();
};

/**
 * In this method the replay string that has been passed directly or downloaded is parsed into a
 * {@link Replay}. Afterwards an attempt is made to start the visualization ({@link Visualizer#tryStart}).
 *
 * @private
 */
Visualizer.prototype.loadParseReplay = function() {
	var vis = this;
	this.progress('Parsing the replay...', function() {
		var debug = vis.state.options['debug'];
		var user = vis.state.options['user'];
		if (user === '') user = undefined;
		if (vis.replayStr) {
			vis.state.replay = new Replay(vis.replayStr, debug, user);
            vis.state.replay.meta.playercolors = [];
			for (var i = 0; i < vis.state.options.playercolors.length; i++) {
				var color = vis.state.options.playercolors[i];
				vis.state.replay.meta.playercolors.push(hexToRgb(color));
			}
//            vis.state.options.playercolors = [];
//            for (var i = 0; i < vis.state.replay.meta.playercolors.length; i++) {
//				var color = vis.state.replay.meta.playercolors[i];
//				vis.state.options.playercolors.push(hexToRgb(color));
//			}
			vis.replayStr = undefined;
		} else if (vis.loading !== LoadingState.CLEANUP) {
			throw new Error('Replay is undefined.');
		}
		vis.tryStart();
	}, "PARSE");
};

/**
 * Creates the main canvas element and insert it into the web page. An attempt is made to start the
 * visualization ({@link Visualizer#tryStart}).
 *
 * @private
 */
Visualizer.prototype.loadCanvas = function() {
	var vis = this;
	this.progress('Creating canvas...', function() {
		if (!vis.main.canvas) {
			vis.main.canvas = document.createElement('canvas');
			vis.main.canvas.style.display = 'none';
		}
		var c = vis.main.canvas;
		vis.main.ctx = c.getContext('2d');
		if (vis.container.firstChild !== c) {
			vis.container.insertBefore(c, vis.log);
		}
		vis.tryStart();
	}, "CANVAS");
};

/**
 * Called by the ImageManager when no more images are loading. Since image loading is a background
 * operation, an attempt is made to start the visualization ({@link Visualizer#tryStart}). If some
 * images didn't load, the visualizer is stopped with an error message.
 *
 * @param error
 *        {String} Contains the error message for images that didn't load or is empty.
 */
Visualizer.prototype.completedImages = function(error) {
	if (error) {
		this.errorOut(error, true);
	} else {
		this.tryStart();
	}
};

/**
 * Checks if we have a drawing context (canvas/applet), the images and the replay. If all components
 * are loaded, some remaining items that depend on them are created and playback is started.
 * tryStart() is called after any long during action that runs in the background, like downloading
 * images and the replay to check if that was the last missing component.
 *
 * @private
 */
Visualizer.prototype.tryStart = function() {
	var bg, i, k, dlg, scores;
	var vis = this;
	// we need to parse the replay, unless it has been parsed by the
	// XmlHttpRequest callback
	if (this.state.replay) {
		if (!this.main.ctx) return;
		if (this.imgMgr.pending !== 0) return;

		// colorize all objects
		var colors = this.state.options.playercolors;

        this.imgMgr.patterns['ship1'] = this.imgMgr.images['ship_p1'];
        this.imgMgr.patterns['ship2'] = this.imgMgr.images['ship_p2'];
        this.imgMgr.patterns['treasureOnShipV1'] = this.imgMgr.images['treasure_on_shipV1'];
        this.imgMgr.patterns['treasureOnShipV2'] = this.imgMgr.images['treasure_on_shipV2'];
        this.imgMgr.patterns['treasureOnShipV3'] = this.imgMgr.images['treasure_on_shipV3'];
        this.imgMgr.patterns['treasureOnShipV4'] = this.imgMgr.images['treasure_on_shipV4'];
        this.imgMgr.patterns['treasureOnShipV5'] = this.imgMgr.images['treasure_on_shipV5'];
        this.imgMgr.patterns['treasureOnShipV6'] = this.imgMgr.images['treasure_on_shipV6'];
        this.imgMgr.patterns['drunk'] = this.imgMgr.images['drunk'];
        this.imgMgr.patterns['robPowerupOnShip'] = this.imgMgr.images['ship_with_rob_powerup'];
        this.imgMgr.patterns['speedPowerupOnShip'] = this.imgMgr.images['ship_with_speed_powerup'];
        this.imgMgr.patterns['attackPowerupOnShip'] = this.imgMgr.images['ship_with_attack_powerup'];

        /* Do not load boards on the site */
		this.map.boardA = this.imgMgr.images['boardA'];
		/*this.map.boardB = this.imgMgr.images['boardB'];
		this.map.boardC = this.imgMgr.images['boardC'];
		*/
        this.map.ship1 = this.imgMgr.patterns['ship1'];
		this.map.ship2 = this.imgMgr.patterns['ship2'];
		this.map.drunk = this.imgMgr.patterns['drunk'];
		this.map.treasureOnShipV1 = this.imgMgr.patterns['treasureOnShipV1'];
		this.map.treasureOnShipV2 = this.imgMgr.patterns['treasureOnShipV2'];
		this.map.treasureOnShipV3 = this.imgMgr.patterns['treasureOnShipV3'];
		this.map.treasureOnShipV4 = this.imgMgr.patterns['treasureOnShipV4'];
		this.map.treasureOnShipV5 = this.imgMgr.patterns['treasureOnShipV5'];
		this.map.treasureOnShipV6 = this.imgMgr.patterns['treasureOnShipV6'];

		this.map.barrel = this.imgMgr.images['barrel'];
		this.map.shipDefend = this.imgMgr.images['ship_defend'];

        this.piratesMap.setTreasureImage(
            this.imgMgr.images['treasure_v1'],
            this.imgMgr.images['treasure_v2'],
            this.imgMgr.images['treasure_v3'],
            this.imgMgr.images['treasure_v4'],
            this.imgMgr.images['treasure_v5'],
            this.imgMgr.images['treasure_v6']);
        this.map.robPowerup = this.imgMgr.images['rob_powerup'];
        this.map.robPowerupOnShip = this.imgMgr.patterns['robPowerupOnShip'];
        this.map.speedPowerup = this.imgMgr.images['speed_powerup'];
        this.map.speedPowerupOnShip = this.imgMgr.patterns['speedPowerupOnShip'];
        this.map.attackPowerup = this.imgMgr.images['attack_powerup'];
        this.map.attackPowerupOnShip = this.imgMgr.patterns['attackPowerupOnShip'];

        this.map.script = this.imgMgr.images['script'];
        this.map.script2 = this.imgMgr.images['script2'];

		// add GUI
		if (this.state.options['decorated']) {
			if (this.imgMgr.error) return;
			if (this.imgMgr.pending) return;
			// calculate player order
			if (this.state.replay.meta['replaydata']['bonus']) {
				scores = new Array(this.state.replay.players);
				for (i = 0; i < this.state.replay.players; i++) {
					scores[i] = this.state.replay['scores'][this.state.replay.duration][i];
					scores[i] += this.state.replay.meta['replaydata']['bonus'][i];
				}
			} else {
				scores = this.state.replay['scores'][this.state.replay.duration];
			}
			this.state.ranks = new Array(scores.length);
			this.state.order = new Array(scores.length);
			for (i = 0; i < scores.length; i++) {
				this.state.ranks[i] = 1;
				for (k = 0; k < scores.length; k++) {
					if (scores[i] < scores[k]) {
						this.state.ranks[i]++;
					}
				}
				k = this.state.ranks[i] - 1;
				while (this.state.order[k] !== undefined)
					k++;
				this.state.order[k] = i;
			}
		}
		// calculate speed from duration and config settings
		this.director.duration = this.state.replay.duration;
		this.calculateReplaySpeed();
		if (this.state.options['interactive']) {
			// this will fire once in FireFox when a key is held down
			/**
			 * @ignore
			 * @param event
			 *        The input event.
			 * @returns {Boolean} True, if the browser should handle the event.
			 */
			document.onkeydown = function(event) {
				if (!(event.shiftKey || event.ctrlKey || event.altKey || event.metaKey || (document.activeElement || {}).tagName == "INPUT")) {
					if (Visualizer.focused.keyPressed(event.keyCode)) {
						if (event.preventDefault)
							event.preventDefault();
						else
							event.returnValue = false;
						return false;
					}
				}
				return true;
			};
		}
		// setup mouse handlers
		/**
		 * @ignore
		 * @param event
		 *        The input event.
		 */

		this.main.canvas.onmousemove = function(event) {
			var mx = 0;
			var my = 0;
			var obj = this;
			if (this.offsetParent) do {
				mx += obj.offsetLeft;
				my += obj.offsetTop;
			} while ((obj = obj.offsetParent))
			mx = event.clientX
					- mx
					+ ((window.scrollX === undefined) ? (document.body.parentNode.scrollLeft !== undefined) ? document.body.parentNode.scrollLeft
							: document.body.scrollLeft
							: window.scrollX);
			my = event.clientY
					- my
					+ ((window.scrollY === undefined) ? (document.body.parentNode.scrollTop !== undefined) ? document.body.parentNode.scrollTop
							: document.body.scrollTop
							: window.scrollY);
			vis.mouseMoved(mx, my);
		};

		/** @ignore */
		this.main.canvas.onmouseout = function() {
			vis.mouseExited();
		};
		/**
		 * @ignore
		 * @param event
		 *        The input event.
		 */
		this.main.canvas.onmousedown = function(event) {
			if (event.which === 1) {
				Visualizer.focused = vis;
				vis.mousePressed();
			}
		};
		/**
		 * @ignore
		 * @param event
		 *        The input event.
		 */
		this.main.canvas.onmouseup = function(event) {
			if (event.which === 1) {
				vis.mouseReleased();
			}
		};

		/** @ignore */
		window.onresize = function() {
			vis.resize();
		};
		Visualizer.focused = this;
		// move to a specific row and col
		this.state.shiftX = 0;
		this.state.shiftY = 0;

		this.log.style.display = 'none';
		this.main.canvas.style.display = 'inline';
		this.loading = LoadingState.IDLE;
		this.setFullscreen(this.state.config['fullscreen']);
		if (this.state.replay.hasDuration) {
			if (!isNaN(this.state.options['turn'])) {
				this.director.gotoTick(this.state.options['turn'] - 1);
			} else {
				this.director.play();
			}
		}
	} else if (this.replayStr) {
		this.loadParseReplay();
	}
};

/**
 * Changes the replay speed.
 *
 * @private
 * @param {Number}
 *        modifier {@link Config#speedFactor} is changed by this amount.
 */
Visualizer.prototype.modifySpeed = function(modifier) {
    var speedFactor = this.state.config['speedFactor'] + modifier;
    speedFactor = Math.max(speedFactor, this.state.config['speedSlowestFactor']);
	speedFactor = Math.min(speedFactor, this.state.config['speedFastestFactor']);
	this.state.config['speedFactor'] = speedFactor;
	this.calculateReplaySpeed();
};

/**
 * This calculates the playback speed from the configuration values {@link Config#duration},
 * {@link Config#speedSlowest}, {@link Config#speedFastest} and {@link Config#speedFactor}. The
 * latter can be controlled by the speed buttons.
 *
 * @private
 */
Visualizer.prototype.calculateReplaySpeed = function() {
//	var speed = this.director.duration / this.state.config['duration'];
    var speed = Math.pow(2, this.state.config['speedFactor']);
//	speed = Math.max(speed, this.state.config['speedSlowest']);
//	speed = Math.min(speed, this.state.config['speedFastest']);
//	this.director.defaultSpeed = speed * Math.pow(1.5, this.state.config['speedFactor']);
	this.director.defaultSpeed = speed;
	if (this.director.speed !== 0) {
		this.director.speed = this.director.defaultSpeed;
	}
};

/**
 * Calculates the visualizer display size depending on the constructor arguments and whether
 * fullscreen mode is supported and enabled.
 *
 * @private
 * @returns {Size} the size the visualizer should have
 */
Visualizer.prototype.calculateCanvasSize = function() {
	var width, height;
	var embed = this.state.options['embedded'];
	embed = embed || !this.state.config['fullscreen'];
	width = (this.w && embed) ? this.w : this.container.clientWidth;
	height = (this.h && embed) ? this.h : this.container.clientHeight;
	return new Size(width, height);
};

/**
 * Enables or disables fullscreen mode. In fullscreen mode the &lt;body&gt; element is replaced with
 * a new one that contains only the visualizer. For the Java/Rhino version a special setFullscreen()
 * method on the window object is called.
 *
 * @private
 * @param enable
 *        {Boolean} If true, the visualizer will switch to fullscreen mode if supported.
 */
Visualizer.prototype.setFullscreen = function(enable) {
	if (!this.state.options['embedded']) {
		if (window.setFullscreen) {
			this.state.config['fullscreen'] = window.setFullscreen(enable);
		} else {
			this.state.config['fullscreen'] = enable;
			if (enable || this.savedBody) {
				var html = document.getElementsByTagName('html')[0];
				if (enable) {
					this.container.removeChild(this.main.canvas);
					this.savedOverflow = html.style.overflow;
					html.style.overflow = 'hidden';
					var tempBody = document.createElement('body');
					tempBody.appendChild(this.main.canvas);
					this.savedBody = html.replaceChild(tempBody, document.body);
				} else if (this.savedBody) {
					document.body.removeChild(this.main.canvas);
					this.container.appendChild(this.main.canvas);
					html.replaceChild(this.savedBody, document.body);
					html.style.overflow = this.savedOverflow;
					delete this.savedBody;
				}
			}
		}
	}
	this.resize(true);
};

/**
 * Sets a new map zoom. At zoom level 1, the map is displayed such that
 * <ul>
 * <li>it has at least a border of 10 pixels on each side</li>
 * <li>map squares are displayed at an integer size</li>
 * <li>map squares are at least 1 pixel in size</li>
 * </ul>
 * This value is then multiplied by the zoom given to this function and ultimately clamped to a
 * range of [1..ZOOM_SCALE].
 *
 * @private
 * @param zoom
 *        {Number} The new zoom level in pixels. Map squares will be scaled to this value. It will
 *        be clamped to the range [1..ZOOM_SCALE].
 */
Visualizer.prototype.setZoom = function(zoom) {
	var oldScale = this.state.scale;
	var effectiveZoom = Math.max(1, zoom);

	this.state.config['zoom'] = effectiveZoom;
	this.state.scale = Math.max(1, Math.min((this.shiftedMap.w - 2 * this.shiftedMap.padding) / this.state.replay.cols,
		(this.shiftedMap.h - 2 * this.shiftedMap.padding) / this.state.replay.rows)) | 0;
	this.state.scale = Math.min(ZOOM_SCALE, this.state.scale * effectiveZoom);

	if (oldScale) {
		this.state.shiftX = (this.state.shiftX * this.state.scale / oldScale) | 0;
		this.state.shiftY = (this.state.shiftY * this.state.scale / oldScale) | 0;
	}
	this.map.setSize(this.state.scale * this.state.replay.cols, this.state.scale
			* this.state.replay.rows);

	this.map.x = 0;
	this.map.y = 0;
 	this.map.x = (((this.shiftedMap.w - this.map.w) >> 1) + this.shiftedMap.x) | 0;
	this.map.y = this.shiftedMap.padding + this.shiftedMap.y | 0;

	this.piratesMap.setSize(this.map.w, this.map.h);
};

/**
 * Sets the pirate label display mode to a new value.
 *
 * @private
 * @param mode
 *        {Number} 0 = no display, 1 = letters, 2 = global pirate ids
 */
Visualizer.prototype.setPirateLabels = function(mode) {
	var hasDuration = this.state.replay.hasDuration;
	var recap = hasDuration && (mode === 1) !== (this.state.config['label'] === 1);
	this.state.config['label'] = mode;
    if (recap) {
        // Those two lines cause bugs in the visualizer. Why are they here?
		//this.main.ctx.fillStyle = '#fff';
		//this.main.ctx.fillRect(0, 0, this.main.canvas.width, this.main.canvas.height);
		this.resize(true);
	}
};

/**
 * Called upon window size changes to layout the visualizer elements.
 *
 * @private
 * @param forced
 *        {Boolean} If true, the layouting and redrawing is performed even if no size change can be
 *        detected. This is useful on startup or if the canvas content has been invalidated.
 */
Visualizer.prototype.resize = function(forced) {
	var olds = new Size(this.main.canvas.width, this.main.canvas.height);
	var newSize = this.calculateCanvasSize();
	var resizing = newSize.w != olds.w || newSize.h != olds.h;
	if (resizing || forced) {
		var canvas = this.main.canvas;
		var ctx = this.main.ctx;
		if (resizing) {
			canvas.width = newSize.w;
			canvas.height = newSize.h;
			//ctx.fillStyle = '#fff';
			//ctx.fillRect(0, 0, canvas.width, canvas.height);
		}
		if (forced) {
			// because of the zones we want to draw the map again if resize is forced
			this.map.invalid = true;
		}

		// 3. visualizer placement
		this.shiftedMap.x = 0;
		this.shiftedMap.y = 0;
		this.shiftedMap.setSize(newSize.w, newSize.h);

		this.setZoom(this.state.config['zoom']);

		// redraw everything
		this.director.draw(true);
	}
};


/**
 * Redraws the map display and it's overlays. It is called by the {@link Director} and resembles the
 * core of the visualization.
 */
Visualizer.prototype.draw = function() {
	var ctx, w, mx, my;
	var loc = this.shiftedMap;

	// map
	this.shiftedMap.validate();
	this.main.ctx.drawImage(this.shiftedMap.canvas, loc.x, loc.y);

	// mouse cursor (super complicated position calculation)
	ctx = this.main.ctx;
	if (this.state.mouseOverVis) {
		ctx.save();
		ctx.beginPath();
		ctx.rect(loc.x, loc.y, loc.w, loc.h);
		ctx.clip();
		mx = this.mouseX - this.map.x - this.state.shiftX;
		my = this.mouseY - this.map.y - this.state.shiftY;
		mx = Math.floor(mx / this.state.scale) * this.state.scale + this.map.x + this.state.shiftX;
		my = Math.floor(my / this.state.scale) * this.state.scale + this.map.y + this.state.shiftY;
		ctx.strokeStyle = '#000';
		ctx.beginPath();
        ctx.rect(mx + 0.5, my + 0.5, this.state.scale - 1, this.state.scale - 1);
		ctx.stroke();
		ctx.restore();
	}

	// draw hint text
	var hint = this.hint;
	if (hint) {
        ctx.save();
        ctx.font = FONT;
		ctx.textAlign = 'left';
		ctx.textBaseline = 'middle';
		if (ctx.measureText(hint).width > loc.w) {
			do {
				hint = hint.substr(0, hint.length - 1);
			} while (hint && ctx.measureText(hint + '...').width > loc.w);
			if (hint) hint += '...';
		}
		w = ctx.measureText(hint).width;
		ctx.fillStyle = 'rgba(0,0,0,0.3)';
        ctx.fillRect(loc.x+35+this.shiftedMap.padding, loc.y+this.shiftedMap.padding, w, 22);
		ctx.fillStyle = '#fff';
		ctx.fillText(hint, loc.x+35+this.shiftedMap.padding*2, loc.y + 10+this.shiftedMap.padding);
        ctx.restore();
    }

    // Update the external view - if exists
    if (this.state.options.updateExternalView) {
        this.state.options.updateExternalView();
    }

    //debug mode
    if (this.state.options.debug_mode && this.state.options.stop_turns)
    {
        var turn = Math.floor(this.state.time);
        if (!this.director.playing() && turn !== this.director.lastTurnStopped) {
            this.director.lastTurnStopped = turn;
        }
        if (turn !== this.director.lastTurnStopped && turn in this.state.options.stop_turns) {
            this.director.stop();
            this.director.lastTurnStopped = turn;
        }
    }

};

Visualizer.prototype.calculateHint = function() {
	var row = this.state.mouseRow;
	var col = this.state.mouseCol;
	var hint = 'row ' + row + ' | col ' + col;
	var vis = this;
	var turn = vis.director.time | 0;
    var aniAnts = this.state.replay.getTurn(turn);
	aniAnts.forEach(function(pirate) {
		var x = Math.round(pirate.keyFrameCache.x);
		var y = Math.round(pirate.keyFrameCache.y);

		if (y === row && x === col && (pirate.death === undefined || pirate.death > turn-1) &&
			pirate.keyFrameCache.pirateGameId !== undefined) {
			hint += ' | pirate ' + pirate.keyFrameCache.pirateGameId;
		}
	});

	this.state.replay.meta['replaydata']['treasures'].forEach(function(treasure) {
		var x = Math.round(treasure[1][1]);
		var y = Math.round(treasure[1][0]);

		if (y === row && x === col && (treasure[3][turn-1] === '1' || turn === 0)) {
			hint += ' | treasure ' + treasure[0];
		}
	});

	this.hint = hint;
};

/**
 * Internal wrapper around mouse move events.
 *
 * @private
 * @param mx
 *        {Number} the X coordinate of the mouse relative to the upper-left corner of the
 *        visualizer.
 * @param my
 *        {Number} the Y coordinate of the mouse relative to the upper-left corner of the
 *        visualizer.
 */
Visualizer.prototype.mouseMoved = function(mx, my) {
	var deltaX = mx - this.mouseX;
	var deltaY = my - this.mouseY;
	var oldHint = this.hint;
	var btn = null;
	this.mouseX = mx;
	this.mouseY = my;
	this.state.mouseCol = (Math.wrapAround(mx - this.map.x - this.state.shiftX, this.state.scale
			* this.state.replay.cols) / this.state.scale) | 0;
	this.state.mouseRow = (Math.wrapAround(my - this.map.y - this.state.shiftY, this.state.scale
			* this.state.replay.rows) / this.state.scale) | 0;
	this.hint = '';
	if (this.state.options['interactive']) {
		var realLocX = mx - this.map.x - this.state.shiftX;
		var realLocY = my - this.map.y - this.state.shiftY;
		this.state.mouseOverVis =
				realLocX >= 0 &&
				realLocX < (this.state.scale * this.state.replay.cols) &&
				realLocY >= 0 &&
				realLocY < (this.state.scale * this.state.replay.rows);

		if (this.state.mouseOverVis) {
			this.calculateHint();
		}
//		if (this.mouseDown) {
//			this.state.shiftX += deltaX;
//			this.state.shiftY += deltaY;
//			this.director.draw();
//		}
	}
	if (btn && btn.hint) {
		this.hint = btn.hint;
	}
	if (oldHint !== this.hint) {
		this.director.draw();
	}
};

/**
 * Internal wrapper around mouse down events.
 *
 * @private
 */
Visualizer.prototype.mousePressed = function() {
	if (this.state.options['interactive']) {
		if (this.shiftedMap.contains(this.mouseX, this.mouseY)) {
			this.mouseDown = true;
		    this.mouseMoved(this.mouseX, this.mouseY);
        }
	}
};

/**
 * Internal wrapper around mouse button release events.
 *
 * @private
 */
Visualizer.prototype.mouseReleased = function() {
	this.mouseDown = false;
	this.mouseMoved(this.mouseX, this.mouseY);
};

/**
 * Internal wrapper around mouse exit window events.
 *
 * @private
 */
Visualizer.prototype.mouseExited = function() {
	this.mouseDown = false;
};

/**
 * Internal wrapper around key press events.
 *
 * @private
 * @param key
 *        A key code for the pressed button.
 * @returns {Boolean} false, if the browser should handle this key and true, if the visualizer
 *          handled the key
 */
Visualizer.prototype.keyPressed = function(key) {
	var d = this.director;
	var tryOthers = true;
	if (!this.state.options['embedded']) {
		tryOthers = false;
		switch (key) {
		case Key.PGUP:
			d.gotoTick(Math.ceil(this.state.time) - 10);
			break;
		case Key.PGDOWN:
			d.gotoTick(Math.floor(this.state.time) + 10);
			break;
		case Key.HOME:
			d.gotoTick(0);
			break;
		case Key.END:
			d.gotoTick(d.duration);
			break;
		default:
			tryOthers = true;
		}
	}
	if (tryOthers) {
		switch (key) {
		case Key.SPACE:
			d.playStop();
			break;
		case Key.LEFT:
			d.gotoTick(Math.ceil(this.state.time) - 1);
			break;
		case Key.RIGHT:
			d.gotoTick(Math.floor(this.state.time) + 1);
			break;
		case Key.PLUS:
		case Key.PLUS_OPERA:
		case Key.PLUS_JAVA:
		case Key.UP:
			this.modifySpeed(+1);
			break;
		case Key.MINUS:
		case Key.MINUS_JAVA:
		case Key.DOWN:
			this.modifySpeed(-1);
			break;
		default:
			switch (String.fromCharCode(key)) {
			case 'F':
				this.setFullscreen(!this.state.config['fullscreen']);
				break;
			default:
				return false;
			}
		}
	}
	return true;
};

/**
 * @class This class defines startup options that are enabling debugging features or set immutable
 *        configuration items for the visualizer instance. The available options are listed in the
 *        field summary and can be set by appending them as a parameter to the URL. For example
 *        '...?game=1&turn=20' will display game 1 and jump to turn 20 immediately. For boolean
 *        values 'true' or '1' are interpreted as true, everything else as false. Be aware that it
 *        is also possible to add a parameter named 'config' to the URL that will be handled
 *        specially by {@link Visualizer} to override {@link Config} settings. Also note that any
 *        additional options should have an initial value that makes it clear wether the setting is
 *        a number, a boolean or a string, because options are passed as strings to the Java applet
 *        and it will parse these strings to the data type it finds in the Options object.
 * @constructor
 * @property {String} data_dir The directory that contains the 'img' directory as a relative or
 *           absolute path. You will get an error message if you forget the tailing '/'.
 * @property {Boolean} interactive Set this to false to disable mouse and keyboard input and hide
 *           the buttons from view.
 * @property {Boolean} decorated Set this to false to hide buttons and statistics. This results in a
 *           'naked' visualizer suitable for small embedded sample maps.
 * @property {Boolean} debug Set this to true, to enable loading of some kinds of partially corrupt
 *           replays and display an FPS counter in the title bar.
 * @property {Boolean} profile Set this to true, to enable rendering code profiling though
 *           'console.profile()' in execution environments that support it.
 * @property {Boolean} embedded Set this to true, to disable the fullscreen option.
 * @property {String} game This is the game number that is used by the game link button for display
 *           and as to create the link URL.
 * @property {Number} col If row and col are both set, the visualizer will draw a marker around this
 *           location on the map and zoom in on it. The value is automatically wrapped around to
 *           match the map dimensions.
 * @property {Number} row See {@link Options#col}.
 * @property {Number} turn If this is set, the visualizer will jump to this turn when playback
 *           starts and stop there. This is often used with {@link Options#col} and
 *           {@link Options#row} to jump to a specific event.
 * @property {String} user If set, the replay will give this user id the first color in the list so
 *           it can easily be identified on the map.
 * @property {Boolean} loop If set, the replay will fade out and start again at the end.
 */
Options = function() {
	this['data_dir'] = '';
	this['interactive'] = true;
	this['decorated'] = true;
	this['debug'] = false;
	this['profile'] = false;
	this['embedded'] = false;
	this['game'] = '';
	this['col'] = NaN;
	this['row'] = NaN;
	this['turn'] = NaN;
	this['user'] = '';
	this['loop'] = false;
};

/**
 * Converts a string parameter in the URL to a boolean value.
 *
 * @param value
 *        {String} the parameter
 * @returns {Boolean} true, if the parameter is either '1' or 'true'
 */
Options.toBool = function(value) {
	return value == '1' || value == 'true';
};

/**
 * @class Holds public variables that need to be accessed from multiple modules of the visualizer.
 * @constructor
 * @property {Number} scale The size of map squares in pixels.
 * @property {Array} ranks Stores the rank of each player.
 * @property {Array} order Stores the ranking order of each player.
 * @property {Replay} replay The currently loaded replay.
 * @property {Number} time The current visualizer time or position in turns, starting with 0 at the
 *           start of 'turn 1'.
 * @property {Number} shiftX X coordinate displacement of the map.
 * @property {Number} shiftY Y coordinate displacement of the map.
 * @property {Boolean} mouseOverVis True, if the mouse is currently in the active area of the map.
 *           This is used to quickly check if mouse-over effects need to be drawn.
 * @property {Number} mouseCol The current wrapped map column, the mouse is hovering over. This
 *           value is only valid when {@link State#mouseOverVis} is true.
 * @property {Number} mouseRow The current wrapped map row, the mouse is hovering over. This value
 *           is only valid when {@link State#mouseOverVis} is true.
 * @property fade Undefined, unless a fade out/in effect is to be drawn. Then this is set to a
 *           rgba() fill style.
 */
function State() {
	this.cleanUp();
	this.options = null;
	this.config = new Config();
}

/**
 * Resets the state to initial values.
 */
State.prototype.cleanUp = function() {
	this.scale = NaN;
	this.ranks = undefined;
	this.order = undefined;
	this.replay = null;
	this.time = 0;
	this.shiftX = 0;
	this.shiftY = 0;
	this.mouseOverVis = false;
	this.mouseCol = undefined;
	this.mouseRow = undefined;
	this.fade = undefined;
};


// DONT DELETE THIS FUNCTION!!!!
// This function is used to create the default sprites for the offline game
// DONT DELETE THIS FUNCTION!!!!
function createSprites() {
	var visualizer = angular.element($('[ng-app]').get(0)).scope().visualizer;

	function drawImage(imageName) {
		var a = document.createElement("a");
		var image = document.createElement("img");
		image.src = visualizer.imgMgr.patterns[imageName].toDataURL();
		image.title = imageName;
		a.appendChild(image);
		a.href = image.src;
		a.download = imageName + "_sprite.png";
		a.style.display = 'block';
		document.body.appendChild(a);
	}

	document.body.innerHTML = "";

}
