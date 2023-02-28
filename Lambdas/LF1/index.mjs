import * as AWS_SQS from "@aws-sdk/client-sqs";
const sqs = new AWS_SQS.SQS({ region: "us-east-1" });


const valid_locations = ["manhattan", "new york city", "new york"];
const valid_cuisines = ["american","chinese", "halal","italian","japanese","mexican"];
const slotSig = ["location", "cuisine", "date", "time", "party_size", "email"];
const prompts = {location:"Where would you like me to search?", cuisine: "What type of food do you want to eat?", date: "On what date would you like to eat?", 
	time: "And at what time?", party_size: "What is the size of your party?",
	email: "Please give me an email that I can send a recommendation to.",};

export const handler = async (event, context, callback) => {
	console.log("event:", JSON.stringify(event));
	const sessionState = event.sessionState || {};
	const sessionAttributes = sessionState.sessionAttributes || {};
	const intent = sessionState.intent;
	const intentName = intent.name;
	console.log(`intentName=${intentName}`);

	switch (intentName) {
		case "GreetingIntent":
			callback(null, elicitIntent(sessionAttributes, "Hello how may I help you today?"));
			break;
		case "Thankyou":
			callback(null, elicitIntent(sessionAttributes, "You're welcome, thank you for using our service."));
			break;
		case "DiningSuggestions":
			let slots = event.sessionState.intent.slots;
			if (event.invocationSource === "DialogCodeHook") {
				const validationResult = checkRequest(slots);
				console.log(validationResult);
				if (!validationResult.isValid) {
					console.log("not valid input");
					slots[`${validationResult.violatedSlot}`] = null;
					callback(
						null,
						elicitSlot(
							sessionAttributes,
							intentName,
							slots,
							validationResult.violatedSlot,
							validationResult.message
						)
					);
					return;
				}
				console.log(slots);

				let nextSlotToElicit = getSlotToElicit(slots);
				console.log("next slot: " + nextSlotToElicit);

				if (nextSlotToElicit) {
					callback(
						null,
						elicitSlot(
							sessionAttributes,
							intentName,
							slots,
							nextSlotToElicit,
							{
								contentType: "PlainText",
								content: prompts[nextSlotToElicit],
							}
						)
					);
					return;
				}
			}
			
			console.log(slots.email.value.interpretedValue)
			console.log(slots.date.value.interpretedValue)
			console.log(slots.cuisine.value.interpretedValue)
			console.log(slots.time.value.interpretedValue)
			console.log(slots.party_size.value.interpretedValue)
			const msg = {email: slots.email.value.interpretedValue,
				date: slots.date.value.interpretedValue,
				cuisine: slots.cuisine.value.interpretedValue,
				time: slots.time.value.interpretedValue,
				party_size: slots.party_size.value.interpretedValue};
				
			console.log(msg)
			
			let response = await sqs.sendMessage({
				//using FIFO Queue was throwing an error bc I didn't give it a MessageGroupID
				QueueUrl: "https://sqs.us-east-1.amazonaws.com/438427517041/restaurant_queue",
				MessageBody: JSON.stringify(msg),
			});
			
			var user_email = slots.email.value.interpretedValue

			callback(
				null,
				wrapUp(event, sessionAttributes, "Fulfilled", {
					contentType: "PlainText",
					content: `Ok, I'm searching for a place that fits your needs now
					and will send my suggestion to the ${user_email} email you provided.`,
				})
			);
			break;
		default:
			callback(
				null,
				elicitIntent(
					sessionAttributes,
					"Hmm I didn't quite understand that, let's try again."
				)
			);
	}
};

let checkRequest = (slots) => {

	const [location, cuisine, party_size, email] = [
		slots.location,
		slots.cuisine,
		slots.party_size,
		slots.email,
	];
	if (location) {
		if (!valid_locations.includes(location.value.resolvedValues[0].toLowerCase())) {
			return buildValidationResult(
				false,
				"location",
				`Unfortunately, ${location.value.originalValue} is not supported at the moment. Please give me a different city.`
			);
		}
	}
	if (cuisine) {
		if (!valid_cuisines.includes(cuisine.value.resolvedValues[0].toLowerCase())) {
			return buildValidationResult(
				false,
				"cuisine",
				`Unfortunately, ${cuisine.value.originalValue} food is not supported at the moment. Please give me a different cuisine.`
			);
		}
	}
	if (party_size) {
		if (party_size.value.resolvedValues.length < 1 || party_size.value.resolvedValues < 1) {
			return buildValidationResult(
				false,
				"party_size",
				"Your party must have at least one person. How many people are in your party?"
			);
		}
	}
	return buildValidationResult(true, null, null);
};

let wrapUp = (event, sessionAttributes, fulfillmentState, message) => {
	event.sessionState.intent.state = fulfillmentState;
	return {
		sessionState: {
			sessionAttributes: sessionAttributes,
			dialogAction: {
				type: "Close",
			},
			intent: event.sessionState.intent,
		},
		messages: [message],
		sessionId: event.sessionId,
	};
};

let buildValidationResult = (isValid, violatedSlot, messageContent) => {
	return {
		isValid: isValid,
		violatedSlot: violatedSlot,
		message: { contentType: "PlainText", content: messageContent },
	};
};


let getSlotToElicit = (slots) => {
	for (let slotName of slotSig) {
		if (!slots[slotName]) {
			return slotName;
		}
	}
};

let elicitSlot = (sessionAttributes, intentName, slots, slotToElicit, message) => {
	return {
		sessionState: {
			sessionAttributes: sessionAttributes,
			intent: {
				name: intentName,
				slots: slots,
			},
			dialogAction: {
				type: "ElicitSlot",
				slotToElicit: slotToElicit,
			},
		},
		messages: [message],
	};
};

let elicitIntent = (sessionAttributes, message) => {
	return {
		sessionState: {
			sessionAttributes: sessionAttributes,
			dialogAction: {
				type: "ElicitIntent",
			},
		},
		messages: [
			{
				contentType: "PlainText",
				content: message,
			},
		],
	};
};
