# pycardcon

A heavily modified port of the card-conjurer method of automatically compositng trading card images. The goal of this project is to provide a simple json structure for a card, and an associated simple structure to manage frames, masks, blends, and their meta data, that is then used to automatically compose an image of the playing card. The hope is to reproduce the functionality provided by the card conjurer text layout code, and its frame management system, while also providing a simple to use, defaults based system for defining card elements. 

This project was created to help with the generation of a custom set, and so assumes a project has a certain structure. The assumption is that a custom set or collection of cards will have a root level directory that contains a folder of resources and meta data, as well as folders of card definition files. The resources folder will contain an images and masks that are common across all cards, or sub collections of cards, present in the folder.

The card files can be organized in whatever manner you need. The original use case was to consider a folder containing multiple directories, one for each of a jump-start list. Each folder contained the card files for the jumpstart lists, a directory containing the art images for the cards in the list, and an output directory. 

The methods provided to render a card only require a path to the card file, its resources, and its output directory. 

## Quick Start

- Clone
- Obtain a resource directory for the TCG of your choice, RESOURCE_DIR
- Create a workspace for cards; 'WORKSPACE_ROOT'
- Create a directory for source images in the workspace; 'WORKSPACE_ROOT/img'
- Create an output directory in the workspace; 'WORKSPACE_ROOT/cards'
- Run the main script of the pycardcon package to watch the root directory for saved changes to .json files:
  * `python -m pycardcon WORKSPACE_ROOT PATH_TO_RESOURCE_DIR WORKSPACE_ROOT/cards`
- Write a card.json file and save it. The above should render it automatically.
  

## Overview
Borrowing heavily from cardconjurer, we treat a trading card as a set of frames, pasted onto an image, sometimes using a mask. Each of these frames may or may not be associated with some text-region, usualy related to that frames purpose. Be that a full card frame containing a title, cost, type, and rules line. Or a small power/loyalty/cost icon with a small text region. Sometimes, a frame might be blended, such that a transparency is applied to the image, allowing compositions like 50/50 cards.  

This package tracks the data about these frames in a card file, that is used to indicate what frames to be used, and other card data. For each frame, you can specify a set of masks, a set of blend images, and a set of text regions you'd like to use from the set of text regions 'offered' by that frame. 

The card file includes a separate text region where, for each of the selected regions from the frames, you can specify the text content and other formatting modifiers. 

To fully render a card, the methods for reading in a card json file will fill in additional, required values for each element based on the defaults defined in the meta files for the frames. This means that for any frame, unless you want to make specific changes to locations and bounds, you can just enter in text, and occasional other modifiers, and the defaults are added in for you automatically. 

This process is done for basically every element of the card. Defaults are defined in meta files contained in the provided resource directory, and used to fill in any missing values not being overwritten by the card author. The next sections will cover the basic structure of a card file, how to specify frames and their masks, and other information about the card using already-written frame packs. The following resources section outlines how a frame pack and its meta files are organized so that they can be used in a card file. 

Once the json file is read in, and the default values are added from the meta files, the package then follows a very similar rendering pipeline, but using the `pillow` module instead of HTML canvases. The text rendering pipeline is an inefficient greedy approach that repaints lines with ever-decreasing font sizes until a render fits inside the defined region. 

An eventual goal of this project is to have a clear distinction between the process of representing, reading, and rendering a card and the definition of any particular card games resource files. The hope is that a particular card games resources (whether covered by some IP law or not) can be fully defined in a separate file or collection of files.  The remaining issues are handling the process of special/bundled card regions (planeswalkers, sagas, levelers) that require additional loading of frames, blends, and shaders at locations that are context specific, as well as arbitrary handling of the art and symbols used in other card locations (copy write/bottom info and the internal symbols used in card text like costs and action symbols).

## Card File 
A card file as the following overall structure.

### Frames

### Masks and Blends

### Text Areas

### Art 

### Set Info


## Resources

### Frame Pack Meta

### Set Symbols

### Fonts


## Example Project

### Structure

### Commands