/**
 * DeepPoker R1 - Frontend JavaScript
 * 
 * Handles game UI, player actions, and server communication.
 * Supports both HTTP API and WebSocket for real-time updates.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ============= DOM Elements =============
    const foldBtn = document.getElementById('fold');
    const checkBtn = document.getElementById('check');
    const callBtn = document.getElementById('call');
    const raiseBtn = document.getElementById('raise');
    const allInBtn = document.getElementById('all-in');
    const raiseSlider = document.getElementById('raise-slider');
    const sliderWrapper = document.querySelector('.slider-wrapper');
    const raisePotThird = document.getElementById('raise-pot-third');
    const raisePotHalf = document.getElementById('raise-pot-half');
    const raisePotFull = document.getElementById('raise-pot-full');
    const raisePot2x = document.getElementById('raise-pot-2x');
    const minRaiseLabel = document.getElementById('min-raise-label');
    const maxRaiseLabel = document.getElementById('max-raise-label');
    const potAmount = document.getElementById('pot-amount');
    const playerSelectionScreen = document.getElementById('player-selection-screen');
    const playerCountSelector = document.getElementById('player-count-selector');
    const gameControls = document.querySelector('.game-controls');

    // Hide game controls initially
    gameControls.classList.add('hidden');

    // ============= Game State =============
    let selectedPlayerCount = 2;
    let ws = null;  // WebSocket connection (optional)

    // ============= Player Selection =============
    function initPlayerSelection() {
        const playerButtons = playerCountSelector.querySelectorAll('.player-count-btn');
        playerButtons.forEach(button => {
            button.addEventListener('click', () => {
                playerButtons.forEach(btn => btn.classList.remove('selected'));
                button.classList.add('selected');
                selectedPlayerCount = parseInt(button.dataset.count);
                playerSelectionScreen.style.display = 'none';
                gameControls.classList.remove('hidden');
                initGameWithPlayerCount(selectedPlayerCount);
            });
        });
        playerButtons[0].classList.add('selected');
    }

    // ============= Game Initialization =============
    function initGameWithPlayerCount(count) {
        fetch('/init_game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_count: count })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(data.error);
                alert(data.error);
                return;
            }
            updateGameState();
            startFirstHand();
        })
        .catch(err => console.error('Init game error:', err));
    }

    function startFirstHand() {
        resetBoardCards();
        
        fetch('/start_hand', { method: 'POST' })
        .then(response => response.json())
        .then(result => {
            if (result.error) {
                console.error(result.error);
                return;
            }
            updateGameState();
        })
        .catch(err => console.error('Start hand error:', err));
    }

    // ============= Game State Update =============
    function updateGameState() {
        fetch('/get_game_state')
        .then(response => response.json())
        .then(state => {
            if (state.error) {
                console.error("Error getting game state:", state.error);
                return;
            }

            const publicInfo = state.public_info;
            const privateInfo = state.private_info;

            // Update pot
            potAmount.textContent = publicInfo.pot;

            // Update actions
            updateAction(publicInfo, privateInfo);

            // Update board
            updateBoard(publicInfo.board);

            // Update players
            updatePlayers(publicInfo.players, publicInfo, privateInfo);
        })
        .catch(err => console.error('Get state error:', err));
    }

    // ============= Action Buttons =============
    function updateAction(publicInfo, privateInfo) {
        if (privateInfo.available_moves && privateInfo.available_moves.length > 0) {
            console.log('Public Info:', publicInfo);
            console.log('Private Info:', privateInfo);

            // Show FOLD
            foldBtn.classList.remove('hidden');
            foldBtn.disabled = false;

            // CHECK or CALL
            if (privateInfo.chips_to_call > 0) {
                checkBtn.classList.add('hidden');
                callBtn.classList.remove('hidden');
                callBtn.textContent = `Call ($${privateInfo.chips_to_call})`;
                callBtn.disabled = false;
            } else {
                if (privateInfo.available_moves.includes('CHECK')) {
                    checkBtn.classList.remove('hidden');
                } else {
                    checkBtn.classList.add('hidden');
                }
                callBtn.classList.add('hidden');
                checkBtn.disabled = false;
            }

            // RAISE
            const canRaise = privateInfo.available_moves.includes('RAISE') || 
                           privateInfo.available_moves.includes('BET');
            updateRaiseControls(canRaise, publicInfo, privateInfo);

            // ALL IN
            allInBtn.classList.remove('hidden');
            const currentPlayer = privateInfo.current_player;
            const playerChips = currentPlayer !== null ? publicInfo.players[currentPlayer].stack : 0;
            allInBtn.disabled = playerChips <= 0;
        } else {
            // Hide all action buttons
            foldBtn.classList.add('hidden');
            checkBtn.classList.add('hidden');
            callBtn.classList.add('hidden');
            raiseBtn.classList.add('hidden');
            sliderWrapper.classList.add('hidden');
        }
    }

    function updateRaiseControls(canRaise, publicInfo, privateInfo) {
        if (canRaise) {
            raiseBtn.classList.remove('hidden');
            sliderWrapper.classList.remove('hidden');
        } else {
            raiseBtn.classList.add('hidden');
            sliderWrapper.classList.add('hidden');
            return;
        }

        if (privateInfo.raise_range) {
            console.log('last_raise:', publicInfo.last_raise);
            console.log('min_raise:', privateInfo.min_raise);
            console.log('current_bet:', privateInfo.current_bet);
            console.log('raise_range:', privateInfo.raise_range.min, privateInfo.raise_range.max);
            console.log('chips_to_call:', privateInfo.chips_to_call);

            const minRaiseTotal = privateInfo.raise_range.min;
            const maxRaise = privateInfo.raise_range.max;
            const raiseIncrement = minRaiseTotal - privateInfo.current_bet;

            raiseBtn.textContent = `Raise to $${minRaiseTotal}(+$${raiseIncrement})`;

            // Set slider range
            raiseSlider.min = minRaiseTotal;
            raiseSlider.max = maxRaise;
            raiseSlider.value = minRaiseTotal;

            minRaiseLabel.textContent = `Min: $${minRaiseTotal}`;
            maxRaiseLabel.textContent = `Max: $${maxRaise}`;

            // Pot raise buttons
            if (privateInfo.pot_raise_values) {
                const raiseButtons = [
                    { button: raisePotThird, data: privateInfo.pot_raise_values.pot_third, label: '1/3 Pot' },
                    { button: raisePotHalf, data: privateInfo.pot_raise_values.pot_half, label: '1/2 Pot' },
                    { button: raisePotFull, data: privateInfo.pot_raise_values.pot_full, label: '1x Pot' },
                    { button: raisePot2x, data: privateInfo.pot_raise_values.pot_2x, label: '2x Pot' }
                ];

                const currentPlayer = privateInfo.current_player;
                const playerChips = currentPlayer !== null ? publicInfo.players[currentPlayer].stack : 0;

                raiseButtons.forEach(item => {
                    if (item.data.valid && item.data.total <= playerChips) {
                        item.button.disabled = false;
                        item.button.textContent = `${item.label} ($${item.data.total})`;
                        item.button.dataset.raiseAmount = item.data.total;
                    } else {
                        item.button.disabled = true;
                        item.button.textContent = `${item.label}`;
                    }
                });

                raiseSlider.disabled = false;

                raiseSlider.oninput = function() {
                    const value = parseInt(this.value);
                    const increment = value - privateInfo.current_bet;
                    raiseBtn.textContent = `Raise to $${value}(+$${increment})`;
                    raiseBtn.dataset.raiseAmount = value;
                };

                raiseBtn.dataset.raiseAmount = minRaiseTotal;
            }
        }
    }

    // ============= Board Update =============
    function updateBoard(board) {
        for (let i = 1; i <= 5; i++) {
            const cardElement = document.getElementById(`board-${i}`);
            const card = board[i - 1];

            if (card) {
                const cardText = card.text;
                const cardClass = card.color;

                const needsFlipAnimation = cardElement.className === 'card-placeholder' ||
                    !cardElement.classList.contains('flipped');

                if (needsFlipAnimation) {
                    cardElement.textContent = '';
                    cardElement.className = 'card';

                    const cardBack = document.createElement('div');
                    cardBack.className = 'card-back';
                    cardElement.appendChild(cardBack);

                    const cardFront = document.createElement('div');
                    cardFront.className = `card-front ${cardClass}`;
                    cardFront.innerHTML = cardText;
                    cardElement.appendChild(cardFront);

                    setTimeout(() => {
                        cardElement.classList.add('flipped');
                    }, 300 * (i - 1));
                }
            } else {
                cardElement.textContent = '';
                cardElement.className = 'card-placeholder';
                cardElement.classList.remove('flipped');
            }
        }
    }

    // ============= Players Update =============
    function updatePlayers(players, publicInfo, privateInfo) {
        const playersContainer = document.querySelector('.players-container');
        playersContainer.innerHTML = '';

        console.log('Players state:', players.map(p => ({ id: p.id, state: p.state })));

        const dealerPosition = publicInfo.dealer_position;
        const smallBlindPosition = publicInfo.small_blind_position;
        const bigBlindPosition = publicInfo.big_blind_position;
        const playerCount = players.length;

        players.forEach(player => {
            const playerDiv = document.createElement('div');
            playerDiv.className = 'player';

            const isCurrentPlayer = player.id === String(privateInfo.current_player);
            const isOutPlayer = player.state.includes('OUT');
            if (isCurrentPlayer) playerDiv.classList.add('active');
            if (isOutPlayer) playerDiv.classList.add('out');

            playerDiv.dataset.playerId = player.id;
            playerDiv.classList.add(`player-position-${playerCount}-${player.id}`);

            let handHtml = '';
            // Show cards only for current player
            if (isCurrentPlayer && privateInfo.hand && privateInfo.hand.length > 0) {
                handHtml = `
                    <div class="player-hand">
                        ${privateInfo.hand.map(card => `
                            <div class="card ${card.color}">
                                ${card.text}
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            playerDiv.innerHTML = `
                <div class="player-info">
                    <div class="player-name">Player ${parseInt(player.id) + 1}</div>
                    <div class="player-stack">$${player.stack}</div>
                    <div class="player-bet">Bet: $${player.bet}</div>
                    <div class="player-hand">${handHtml}</div>
                </div>
            `;

            // Position indicators
            const indicatorsContainer = document.createElement('div');
            indicatorsContainer.className = 'position-indicators';
            playerDiv.appendChild(indicatorsContainer);

            if (dealerPosition !== null && dealerPosition === parseInt(player.id)) {
                const dealerButton = document.createElement('div');
                dealerButton.className = 'position-indicator dealer-button';
                dealerButton.textContent = 'D';
                indicatorsContainer.appendChild(dealerButton);
            }

            if (smallBlindPosition !== null && smallBlindPosition === parseInt(player.id)) {
                const sbButton = document.createElement('div');
                sbButton.className = 'position-indicator small-blind-button';
                sbButton.textContent = 'SB';
                indicatorsContainer.appendChild(sbButton);
            }

            if (bigBlindPosition !== null && bigBlindPosition === parseInt(player.id)) {
                const bbButton = document.createElement('div');
                bbButton.className = 'position-indicator big-blind-button';
                bbButton.textContent = 'BB';
                indicatorsContainer.appendChild(bbButton);
            }

            playersContainer.appendChild(playerDiv);
        });
    }

    // ============= Victory Animation =============
    function showVictoryAnimation(winners, playersCards, potAmountVal, boardCards) {
        const overlay = document.createElement('div');
        overlay.className = 'victory-overlay';
        document.body.appendChild(overlay);

        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                document.body.removeChild(overlay);
                startNextHand();
            }
        });

        const animationContainer = document.createElement('div');
        animationContainer.className = 'victory-animation';
        overlay.appendChild(animationContainer);

        const title = document.createElement('h2');
        title.textContent = '手牌结束!';
        title.className = 'victory-title';
        animationContainer.appendChild(title);

        // All players' cards
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'all-players-cards';
        animationContainer.appendChild(cardsContainer);

        playersCards.forEach(player => {
            const playerCardDiv = document.createElement('div');
            const isWinner = winners.some(w => w.id === player.id);
            if (isWinner) playerCardDiv.classList.add('winner');

            const playerInfo = document.createElement('div');
            playerInfo.className = 'player-info';

            const playerName = document.createElement('span');
            playerName.className = 'player-name';
            playerName.textContent = `玩家 ${parseInt(player.id) + 1}`;
            playerInfo.appendChild(playerName);

            if (isWinner) {
                const winnerBadge = document.createElement('span');
                winnerBadge.className = 'winner-badge';
                winnerBadge.textContent = '赢家!';
                playerInfo.appendChild(winnerBadge);

                const winner = winners.find(w => w.id === player.id);
                if (winner) {
                    const initialStack = Math.round(winner.stack - winner.won);
                    const finalStack = Math.round(winner.stack);
                    const wonAmount = Math.round(winner.won);

                    const stackDiv = document.createElement('div');
                    stackDiv.className = 'winner-stack';
                    stackDiv.appendChild(document.createTextNode('筹码: '));

                    const initialStackSpan = document.createElement('span');
                    initialStackSpan.className = 'initial-stack';
                    initialStackSpan.textContent = `$${initialStack}`;
                    stackDiv.appendChild(initialStackSpan);

                    stackDiv.appendChild(document.createTextNode(' + '));

                    const wonAmountSpan = document.createElement('span');
                    wonAmountSpan.className = 'won-amount';
                    wonAmountSpan.textContent = '$0';
                    stackDiv.appendChild(wonAmountSpan);

                    stackDiv.appendChild(document.createTextNode(' = '));

                    const finalStackSpan = document.createElement('span');
                    finalStackSpan.className = 'final-stack';
                    finalStackSpan.textContent = `$${initialStack}`;
                    stackDiv.appendChild(finalStackSpan);

                    playerInfo.appendChild(stackDiv);

                    // Animate numbers
                    const animationDuration = 2000;
                    const fps = 30;
                    const steps = animationDuration / 1000 * fps;
                    const increment = wonAmount / steps;

                    let currentWonAmount = 0;
                    let currentFinalStack = initialStack;
                    let step = 0;

                    const animateNumbers = () => {
                        currentWonAmount += increment;
                        currentFinalStack = initialStack + currentWonAmount;

                        if (currentWonAmount >= wonAmount || step >= steps) {
                            wonAmountSpan.textContent = '$' + wonAmount;
                            finalStackSpan.textContent = '$' + finalStack;
                        } else {
                            wonAmountSpan.textContent = '$' + Math.round(currentWonAmount);
                            finalStackSpan.textContent = '$' + Math.round(currentFinalStack);
                            step++;
                            requestAnimationFrame(animateNumbers);
                        }
                    };

                    setTimeout(() => requestAnimationFrame(animateNumbers), 500);
                }
            }

            playerCardDiv.appendChild(playerInfo);

            // Player cards
            const cardsDiv = document.createElement('div');
            cardsDiv.className = 'player-cards';
            player.cards.forEach(card => {
                const cardDiv = document.createElement('div');
                cardDiv.className = `card ${card.color}`;
                cardDiv.textContent = card.text;
                cardsDiv.appendChild(cardDiv);
            });
            playerCardDiv.appendChild(cardsDiv);

            cardsContainer.appendChild(playerCardDiv);
        });

        // Board cards
        const boardContainer = document.createElement('div');
        boardContainer.className = 'board-cards-container';
        animationContainer.appendChild(boardContainer);

        const boardTitle = document.createElement('div');
        boardTitle.className = 'board-title';
        boardTitle.textContent = '公共牌';
        boardContainer.appendChild(boardTitle);

        const boardCardsDiv = document.createElement('div');
        boardCardsDiv.className = 'board-cards';
        boardCards.forEach(card => {
            const cardDiv = document.createElement('div');
            cardDiv.className = `card ${card.color}`;
            cardDiv.textContent = card.text;
            boardCardsDiv.appendChild(cardDiv);
        });
        boardContainer.appendChild(boardCardsDiv);

        // Next hand button
        const nextHandBtn = document.createElement('button');
        nextHandBtn.className = 'next-hand-btn';
        nextHandBtn.textContent = '下一局';
        nextHandBtn.style.display = 'block';
        nextHandBtn.style.fontSize = '20px';
        nextHandBtn.style.padding = '15px 30px';
        nextHandBtn.style.marginTop = '30px';
        animationContainer.appendChild(nextHandBtn);

        nextHandBtn.addEventListener('click', () => {
            document.body.removeChild(overlay);
            startNextHand();
        });
    }

    function startNextHand() {
        fetch('/start_hand', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(data.error);
                alert(data.error);
                return;
            }
            resetBoardCards();
            updateGameState();
        })
        .catch(err => console.error('Start next hand error:', err));
    }

    function resetBoardCards() {
        for (let i = 1; i <= 5; i++) {
            const cardElement = document.getElementById(`board-${i}`);
            cardElement.textContent = '';
            cardElement.className = 'card-placeholder';
            cardElement.classList.remove('flipped');
        }
    }

    // ============= Take Action =============
    function takeAction(actionType, amount = null) {
        const data = { action_type: actionType };
        if (amount !== null) {
            data.amount = amount;
        }

        fetch('/take_action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.error) {
                console.error("Error taking action:", result.error);
                return;
            }

            updateGameState();

            if (result.winners) {
                const playersCards = result.players_cards;
                const potAmountVal = result.pot;
                const boardCards = result.board;
                showVictoryAnimation(result.winners, playersCards, potAmountVal, boardCards);
            }
        })
        .catch(err => console.error('Take action error:', err));
    }

    // ============= Event Listeners =============
    foldBtn.addEventListener('click', () => takeAction('FOLD'));
    checkBtn.addEventListener('click', () => takeAction('CHECK'));
    callBtn.addEventListener('click', () => takeAction('CALL'));

    raiseBtn.addEventListener('click', () => {
        const raiseAmount = parseInt(raiseBtn.dataset.raiseAmount);
        takeAction('RAISE', raiseAmount);
    });

    const quickRaiseButtons = [raisePotThird, raisePotHalf, raisePotFull, raisePot2x];
    quickRaiseButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (!button.disabled) {
                const amount = parseInt(button.dataset.raiseAmount);
                raiseSlider.value = amount;
                takeAction('RAISE', amount);
            }
        });
    });

    allInBtn.addEventListener('click', () => {
        takeAction('ALL_IN');
    });

    // ============= Initialize =============
    initPlayerSelection();
});
