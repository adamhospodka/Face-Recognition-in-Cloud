// In each file we tell Webpack what are the dependencies
import { greeting, randomHash } from './side.js'
import { sas_token, sas_token_input_videos_1, orchestratorURL, containerName, inputContainerURL } from './secrets'
import * as d3 from 'd3';
const { BlobServiceClient } = require("@azure/storage-blob");

// Test of external script
console.log(greeting)

/* DOM elements */
const fileInput = document.getElementById("file-input");
const fileList = document.getElementById("file-list");
const movieClipInput = document.getElementById("file-input");

/* Azure variables */
const blobSasUrl = sas_token_input_videos_1;
const blobServiceClient = new BlobServiceClient(blobSasUrl);
const orchestratorURL = orchestratorURL
const containerName = containerName
const containerClient = blobServiceClient.getContainerClient(containerName);
const inputContainerURL = inputContainerURL

/* Logic variables */
var orchestratorHandle;


const callOrchestrator = async (movieName, clipUrl) => {

  /**
   * Calls Azure orchestrator in fixed URL.
   * Fills orchestratorHandle global variables.
   * 
   * @param  {string} movieName Movie name from user input
   * @param  {string} clipUrl   Direct public blob storage URL
   * @return {string} void
   */

  
  let body = JSON.stringify({
    "probableMovieName": movieName,
    "inputMovieUrl": clipUrl
  })

  let response = await fetch(orchestratorURL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body
  })
  let data = await response.json();
  data = JSON.stringify(data);
  data = JSON.parse(data);
  
  orchestratorHandle = data.statusQueryGetUri;
    
  console.log("Request sent (movie " + movieName + ")");
}



const getOrchestratorProperty = async (url, property) => {

  /**
   * Calls Azure orchestrator and retrieves specified property
   * 
   * @param  {string} url            Movie name from user input
   * @param  {string} property       Direct public blob storage URL
   * @return {string} data[property] Desired property of orchestrator
   */

  if (orchestratorHandle == null) {
    console.log("No orchestrator")
    return
  }

  let response = await fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  })

  let data = await response.json();
  data = JSON.stringify(data);
  data = JSON.parse(data);
  
  if (data[property] == "Failed"){
    error.log("There was some mistake when processing video :(");
    return
  }

  console.log(data[property])
  return data[property]
}



const uploadMovieClip = async () => {

  /**
   * Uploads selected file to blob storage and calls orchestrator
   * @return {string} data[property] Desired property of orchestrator
   */

  var fileName;
  var fileExtenstion;
  var newFileName;
  var mimeType;

  try {
    console.log("Uploading movie clip...");
    const promises = [];


    for (const file of fileInput.files) {
      // blobFileName = file.name + randomHash();
      fileName = file.name.split('.')[0]
      fileExtenstion = file.name.split('.')[1]
      newFileName = fileName + randomHash() + '.' + fileExtenstion;

      // Select right file type
      switch(fileExtenstion){
        case 'mov':
          mimeType = 'video/quicktime';
          break;
        case 'avi': 
          mimeType = 'video/x-msvideo';
          break;
        case 'mp4': 
          mimeType = 'video/mp4';
          break;
        default:
          console.error("File must be [mp4, avi, mov file] type");
          return
          
      };

      const blockBlobClient = containerClient.getBlockBlobClient(newFileName);
      const blobOptions = {
        blobHTTPHeaders: { blobContentType: mimeType }
      };

      promises.push(blockBlobClient.uploadBrowserData(file, blobOptions));
    }
    await Promise.all(promises);

    console.log("Clip uploaded");

  }
  catch (error) {
    console.log(error.message);
  }

  let movieName = d3.select('#input-name').node().value
  let clipUrl = inputContainerURL + newFileName
  console.log("Calling orchestrator with (movie: " + movieName + "\n" + "clip url: " + clipUrl)
  callOrchestrator(movieName, clipUrl)
}



/* Button reactivity */

// Upload movies
d3.select('#upload-movie-clip-button').on("click", () => {

  let is_input_null = d3.select('#input-name').node().value == null;
  let is_input_empty = d3.select('#input-name').node().value == '';

  if (is_input_null || is_input_empty) {
    console.log("No movie name entered")
    return
  }

  // Activate file upload
  movieClipInput.click()

});

// File input (private)
d3.select('#file-input').on("change", () => {uploadMovieClip()})


// Get running status of orcehstrator
d3.select('#get-orchestrator-status').on("click", function () {
  getOrchestratorProperty(orchestratorHandle, "runtimeStatus")
})

// Render acttors tables
d3.select('#render-actors').on("click", function () {

  if (orchestratorHandle == null) {
    console.log("No orchestrator")
    return
  }

  // If result not ready, return
  getOrchestratorProperty(orchestratorHandle, "runtimeStatus").then(
    response => {
      if (response == 'Running' || response == 'Pending') {
        console.log("Results not ready... Try in a while")
        return
      }
    })

  // Render results
  try {
    getOrchestratorProperty(orchestratorHandle, "output").then(
      response => { render_actors(response); })
  }
  catch (error) {
    console.log(error.message);
  }
})


function render_actors(response){
  
  /* Defines functions for transformation of incoming request into d3-friendly cormat, computes distinct actors and theirs counts and plots two HTML tables with information */


  function transform_data(json_data) {
    /* Object of keys into array of objects */

    return Object.keys(json_data).map(function(key){
        return {frame: key, actors: json_data[key]}
    })
  
  }
  
  function get_unique_actors(json_data){
    /* Extracts unique actors name and their counts and saves into global vars */
    
    for (let frame of Object.keys(json_data)){ 
      for (let actor of json_data[frame]){
        if (distinct_actors.includes(actor)) {
          actor_counts[actor] += 1;
        }
        else{
          distinct_actors.push(actor)
          actor_counts[actor] = 1;
        }
      }
    }
  
    return
  }


  var actor_counts = {}
  var distinct_actors = []

  var columns = ["Frame", "Actors"]
  var rows = transform_data(response)

  get_unique_actors(response) // fills "distinct_actors"
  var unique_actors = distinct_actors

  // Delete tables if already exit
  d3.selectAll("#viz-container, #viz-container2").selectAll("table").remove()
  d3.selectAll("#viz-container, #viz-container").selectAll("p").remove()


  // Detail table
  d3.select('#viz-container').append("p").text("Actors per frame")
  var table_detail = d3.select('#viz-container').append('table');

  table_detail.append('thead').append('tr')
    .selectAll('th')
    .data(columns).enter()
    .append('th')
    .text((d) => d)

  table_detail.append('tbody')
    .selectAll('tr') //row
    .data(rows).enter()
    .append('tr')
    .selectAll('td') //cell
    .data(function (row) {
      return [row.frame, row.actors]
    }).enter()
    .append('td')
    .text((d) => d)


  // Summary table
  d3.select('#viz-container').append("p").text("Number of appearances in frames")
  var table_summary = d3.select('#viz-container2').append('table');
  var summary_columns = ["Actor", "Appearance count"]//, "Misc"]

  table_summary.append('thead').append('tr')
    .selectAll('th')
    .data(summary_columns).enter()
    .append('th')
    .text((d) => d)

  table_summary.append('tbody')
    .selectAll('tr') //row
    .data(unique_actors).enter()
    .append('tr')
    .selectAll('td') //cell
    .data(function (actor) {
      return [actor, actor_counts[actor]]//, 'x']
    }).enter()
    .append('td')
    .text((d) => d)

}
