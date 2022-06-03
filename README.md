# Module 1 Group Assignment

CSCI 5117, Spring 2022, [assignment description](https://canvas.umn.edu/courses/291031/pages/project-1)

## App Info:

- Team Name: The LEAKs
- App Name: paletteify
- App Link: https://frozen-gorge-21119.herokuapp.com/

### Students

- Luisa Jimenez Alarcon jimen215@umn.edu
- Lana Berge berg2789@umn.edu
- Erik Rossing rossi239@umn.edu
- Amelie Elmquist elmqu089@umn.edu
- Khalid Ahmed ahmed935@umn.edu

## Key Features

**Describe the most challenging features you implemented
(one sentence per bullet, maximum 4 bullets):**

- Search By Color - We implemented different techniques-- for instance, when you click one of the 10 color aesthetic buttons under the search bar, we are utilizing a RGB Color Classifier idea, whereas when you click a palette circle under a post image, we are using our own color distance formula.
- Palette Design - Layout, especially for the palettes, was difficult-- dealing with PureCSS grids.
- Favorites Feature - One specific issue we ran into with the favoriting feature was that the page would reload each time a heart was pressed.

## Testing Notes

**Is there anything special we need to know in order to effectively test your app? (optional):**

- There are no notes for testing.

## Screenshots of Site


Home page:    ![Alt text](/images/Home.png?raw=true "Home")
Search page:  ![Alt text](/images/Search.png?raw=true "Search")
Profile page: ![Alt text](/images/Profile.png?raw=true "Profile")
Upload page:  ![Alt text](/images/Upload.png?raw=true "Upload")

## Mock-up

LINK TO OUR FIGMA PROTOTYPE: https://www.figma.com/file/WsJ8sowVenNpUuQe2c2vRN/The-LEAKS-Paletteify-Lofi-Prototype?node-id=0%3A1

## External Dependencies

**Document integrations with 3rd Party code or services here.
Please do not document required libraries. or libraries that are mentioned in the product requirements**

- Color Thief (https://lokeshdhakar.com/projects/color-thief/#api) was used to extract dominant colors from an image input.
- Webcolors (https://medium.com/codex/rgb-to-color-names-in-python-the-robust-way-ec4a9d97a01f) was utilized for conversion from color name to rgb value (for the text input technique of search by color).
- jscolor (https://jscolor.com/) was used for selecting background colors on profile pages.
- RGB Color Classifier (https://medium.com/analytics-vidhya/building-rgb-color-classifier-part-2-8c49a57f6b91) had a helping hand in categorizing rgb values into color categories.
- Font Awesome (https://fontawesome.com/) was used for icons throughout.

**If there's anything else you would like to disclose about how your project
relied on external code, expertise, or anything else, please disclose that
here:**
