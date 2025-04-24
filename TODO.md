# To Do

#### Urgent

- deal with images:
    - [X] fix image size issues (store full size image, but send smaller, based on board?)
    - [X] modify visible map image instead of creating new one?
    - [X] delete unused images
    - [X] change variable name for consistent data handling on image types 
        (figure out where the best place to convert is)
    - [ ] add mask image layer?
    - cache images on server side
- [X] add emit events for joining board
- [X] check join() is not being called extraneously (and propogated)
- [ ] change mask so that the grid data given to user is blocked per square by mask
        (i.e. if there is a token behind the mask, all they get is that there is a mask there)
- [ ] only have updates for owner panel in owner board page
- [ ] switch to default not None for board empty squares
- [ ] deal with tokens: 
    - [ ] make only user tokens show up on page, and only user keybindings
    - [ ] add token to board and only have board-level keybindings override user keybindings
- [ ] only be able to move your own token, unless more user privliges
- [ ] delete token on event

#### Nice

- [ ] add toggle all mask button
- [ ] remove image file when not used (avatar change, token change, map delete)
- [ ] "unique" option for tokens to behave like avatars when placed
- [ ] context menu for editing icons on board
- [ ] more than one thing in a spot
- [ ] page resize should keep board size ratio constant, not location of top left
- [ ] multiple selected squares
- [ ] shift+num to change size of token on board
- [X] save top-left and zoom data in local storage for nice refresh
- [ ] leave board
- [ ] add selected square to local storage


#### Long Term
- [ ] should Map be its own object?
- [ ] draw masking
- [ ] hex grid


