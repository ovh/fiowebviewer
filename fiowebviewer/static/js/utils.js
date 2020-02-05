"use strict"
var llimit = 0;
var rlimit = 0;
var rmax;

var listOfJobs = new Array();
var listOfResults = new Array();
var mode;

function maxWidth(){
    return Math.max.apply(Math,listOfResults.map(function(result){return result.runtime;}))
}

// constructor for Job object
function Job(id, result, types) {
    this.id = id;
    this.result = result;
    this.types = types;
}

// constructor for Result object
function Result(id, name, runtime) {
    this.id = id;
    this.name = name;
    this.runtime = runtime;
}

function fetchMeta(resultsids) {
    return resultsids.map(function(resultid) {
        return $.ajax({
            url: "/api/"+resultid,
            dataType: "json",
        });
    });
}

function calculateGranularity(width, start_frame, end_frame){
    var widthInt = parseInt(width);
    var i = 1;
    var span = parseInt(end_frame - start_frame);
    if(isNaN(span)) return 1;
    while (true && i < 3600){
        /*
         * This function estimates plot width based on data span in miliseconds.
         * First 10 values (1S, 2S, ... , 10S) for aggregation were taken from real aggregation
         * in the application and using that data function had been estimated.
         * Keep in mind that you cannot plot more samples on X axis then actual plot width on screen in pixels.
         * Using this function you can estimate by how many seconds you had to aggregate.
         * This function return first value for which number of points on X axis is lower then box plot width
         * on screen in pixels.
         */
        var tmp = parseInt(span * 0.00125871022496 * Math.pow(1/i, 1.073596));
        if(tmp < width) {
            return i;
        }
        i++;
    }
}

function getYaxisTitle(job, type){
    if(type == "bw") return "MB/s";
    else if(type == "iops") return "iops";
    else return "ms";
}

function getGranularity(difference){
    return `${difference}S`;
}

function showLoading(job, type){
    $(`#plot${type}`).hide(0);
    $(`#plot${type}loader`).show(0);
}

function hideLoading(job, type){
    $(`#plot${type}error`).hide(0);
    $(`#plot${type}`).show(0);
    $(`#plot${type}loader`).hide(0);
}

function showError(job, type){
    $(`#plot${type}`).hide(0);
    $(`#plot${type}loader`).hide(0);
    $(`#plot${type}error`).show(0);
}

function fetchResult(result, job, type, start_frame, end_frame, iotype) {
    if(llimit == 0 && rlimit == 0){
        start_frame = 0;
        end_frame = rmax;
    }
    var width = document.getElementById(`plot${type}wrapper`).clientWidth;
    var granularity = calculateGranularity(width, start_frame, end_frame);
    if(granularity < 1) granularity = 1
    granularity = getGranularity(granularity);
    if(mode == "aggregated") {
        var url = `/api/${result}/${type}.json?start_frame=${start_frame}&end_frame=${end_frame}&granularity=${granularity}&io_type=${iotype}`;
    } else {
        var url = `/api/${result}/${job}/${type}.json?start_frame=${start_frame}&end_frame=${end_frame}&granularity=${granularity}&io_type=${iotype}`;
    }
    showLoading(job, type);
    return $.ajax({
        url: url,
        dataType: "json",
    });
}

function processMeta(resultArray) {
    resultArray.forEach(function(result){
        listOfResults.push(new Result(result["id"], result["name"], result["runtime"]));
        for(var job in result["jobs"]) {
            listOfJobs.push(new Job(job, results[resultArray.indexOf(result)], result["jobs"][job]))
        }
    });
    rmax = maxWidth();
}

function declareZoomInZoomOut(plotdiv, job, type, layout, results, jobs, mode){
    var plotDivId = document.getElementById(plotdiv);
    plotDivId.on('plotly_relayout', function(eventdata){
        if(Number.isFinite(eventdata["xaxis.range[0]"]) && Number.isFinite(eventdata["xaxis.range[1]"])){ // this is to differ zoom-in event from zoom-out.
            console.log("Zoom in");
            llimit = parseInt(eventdata["xaxis.range[0]"]*1000);
            rlimit = parseInt(eventdata["xaxis.range[1]"]*1000);
            if(mode == "detailed"){
                drawAllPlotsDetailed(layout, llimit, rlimit, results, jobs);
            } else {
                drawAllPlots(layout, llimit, rlimit, results, jobs);
            }
        }
    });
    plotDivId.on('plotly_doubleclick', function(){
        console.log("Zoom out");
        if(llimit != 0 && rlimit !=0) {
            llimit = parseInt(llimit - (rlimit - llimit)/2);
            rlimit = parseInt(rlimit + (rlimit - llimit)/2);
            if(llimit < 0 || rlimit > rmax) {
                llimit = 0;
                rlimit = rmax;
            }
            if(mode == "detailed"){
                drawAllPlotsDetailed(layout, llimit, rlimit, results, jobs);
            } else {
                drawAllPlots(layout, llimit, rlimit, results, jobs);
            }
        }
    });
}

function areThereErrors(element, index, array){
    return (element == true);
}

function drawPlot(inputData, job, type, results, jobs, mode) {
    var plotdiv = `plot${type}`;
    var arr = new Array();
    var layout;
    var data;
    var errors = new Array();
    inputData.forEach(function(inputd){
        if(inputd["error"] == "404") {
            errors.push(true);
            return;
        } else {
            errors.push(false);
        }
        data = {
            x: inputd['x'],
            y: inputd['y'],
            mode: 'lines+markers',
            type: 'scatter',
            name: inputd['name'],
            line: { width: 1 },
            marker: { size: 4 },
            connectgaps: false,
        }
        layout = {
            title: type,
            showlegend: true,
            legend: {
                "orientation": "h"
            },
            xaxis: {
                title: 't [s]',
            },
            yaxis: {
                title: getYaxisTitle(job, type),
                fixedrange: true,
                titlefont: {
                    size: 18,
                }
            }
        };
        arr.push(data);
    });
    if(errors.every(areThereErrors)) {
        showError(job, type);
    } else {
        hideLoading(job, type);
        Plotly.newPlot(plotdiv, arr, layout, {
            modeBarButtonsToRemove: ['toImage', 'sendDataToCloud'],
            modeBarButtonsToAdd: [{
                name: 'Download plot as png',
                icon: Plotly.Icons.camera,
                click: function(gd) {
                    Plotly.downloadImage(gd, {
                        width: gd._fullLayout.width,
                        height: gd._fullLayout.height
                    })
                }
            }]
        });
        declareZoomInZoomOut(plotdiv, job, type, layout, results, jobs, mode);
    }
}

function drawAllPlots(layout, llimit, rlimit, results, jobs) {
    var iotypes = ['read', 'write']
    jobs.forEach(function(job){
        job.types.forEach(function(type){
            var promiseArray = new Array();
            var fetchedDataArray = new Array();
            (function(job,type){
                results.forEach(function(result){
                    iotypes.forEach(function(iotype){
                        promiseArray.push(fetchResult(result.id, job.id, type, llimit, rlimit, iotype).then(function(fetchedData){
                            fetchedData['name'] = `${iotype} ${result.name}`;
                            fetchedDataArray.push(fetchedData);
                        }))
                    });
                });
                Promise.all(promiseArray).then(function(){
                    drawPlot(fetchedDataArray, job.id, type, results, jobs, "aggregated");
                });
            })(job,type)
        });
    });
}

function drawAllPlotsDetailed(layout, llimit, rlimit, results, jobs) {
    var iotypes = ['read', 'write']
    results.forEach(function(result){
        jobs[0].types.forEach(function(type){
            var promiseArray = new Array();
            var fetchedDataArray = new Array();
            jobs.forEach(function(job){
                (function(job,type){
                    iotypes.forEach(function(iotype){
                        promiseArray.push(fetchResult(result.id, job.id, type, llimit, rlimit, iotype).then(function(fetchedData){
                            fetchedData['name'] = `${iotype} Job:${job.id} ${result.name}`;
                            fetchedDataArray.push(fetchedData);
                        }));
                    });
                })(job,type)
                Promise.all(promiseArray).then(function(){
                    drawPlot(fetchedDataArray, job.id, type, results, jobs, "detailed");
                });
            });
        });
    });
}

function startPlotting(modeLocal){
    mode = modeLocal;
    Promise.all(fetchMeta(results)).then(function(resultArray){
        processMeta(resultArray);
        if(mode == "aggregated") {
            drawAllPlots(undefined, undefined, undefined, listOfResults, [listOfJobs[0]]); // async!
            $(`#bn-fio-reset`).click(function(){
                drawAllPlots(undefined, 0, rmax, listOfResults, [listOfJobs[0]], "aggregated"); // async!
            });
        }
        if(mode == "detailed"){
            drawAllPlotsDetailed(undefined, undefined, undefined, listOfResults, listOfJobs); // async!
            $(`#bn-fio-reset`).click(function(){
                drawAllPlotsDetailed(undefined, 0, rmax, listOfResults, listOfJobs, "detailed"); // async!
            });
        }
    });
}
